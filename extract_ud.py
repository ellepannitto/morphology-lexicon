#!/usr/bin/env python3
"""Extract UD morphology lexicons from the Italian UD treebank clones.

For each treebank (ISDT, PoSTWITA, ParlaMint) reads every *.conllu split and
produces  it_<name>_ud.tsv  (FORM LEMMA UPOS FEATS)  plus a .counts.tsv.

Two normalisation steps, in this order:
  1. Ambiguity filter: for a wordform with >1 analysis (a distinct
     FORM/LEMMA/UPOS/FEATS tuple), drop any analysis attested in < MIN_SHARE
     of that form's tokens. Single-analysis forms are always kept.
  2. Collapse underspecified Gender/Number: per (FORM, LEMMA, UPOS), entries
     that differ only by Gender Masc/Fem or Number Sing/Plur are merged with
     that feature removed (same rule as the Morph-it conversion).
"""
import glob
import sys
from collections import defaultdict

from udlex import norm_feats, feats_str, feats_to_dict, collapse_underspecified, \
    iter_conllu_tokens

MIN_SHARE = 0.10
TREEBANKS = {
    "isdt": "UD_Italian-ISDT/it_isdt-ud-*.conllu",
    "postwita": "UD_Italian-PoSTWITA/it_postwita-ud-*.conllu",
    "parlamint": "UD_Italian-ParlaMint/it_parlamint-ud-*.conllu",
}


def extract(name, pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        sys.stderr.write(f"[{name}] no files match {pattern}\n")
        return

    by_form = defaultdict(lambda: defaultdict(int))
    n_tok = 0
    for path in files:
        for form, lemma, upos, feats in iter_conllu_tokens(path):
            by_form[form][(form, lemma, upos, norm_feats(feats))] += 1
            n_tok += 1

    # step 1: ambiguity filter, keep counts
    kept = defaultdict(list)  # (form, lemma, upos) -> [(feats_dict, count), ...]
    n_dropped = 0
    for form, analyses in by_form.items():
        total = sum(analyses.values())
        ambiguous = len(analyses) > 1
        for (f, lemma, upos, feats), count in analyses.items():
            if ambiguous and count / total < MIN_SHARE:
                n_dropped += 1
                continue
            kept[(f, lemma, upos)].append((feats_to_dict(feats), count, count / total))

    # step 2: collapse underspecified Gender/Number (sum counts of merged rows)
    out_rows = []  # (form, lemma, upos, feats_str, count, share)
    n_collapsed = 0
    for (form, lemma, upos), items in kept.items():
        dicts = [d for d, _, _ in items]
        before = {frozenset(d.items()) for d in dicts}
        merged = collapse_underspecified(dicts)
        after = {frozenset(d.items()) for d in merged}
        if after != before:
            n_collapsed += 1
        # redistribute counts: a collapsed entry gets the sum of the originals
        # whose dict reduces to it
        def reduce_to(d):
            cands = [m for m in merged if m.items() <= d.items()]
            if not cands:
                return frozenset(d.items())
            return frozenset(max(cands, key=len).items())
        agg = defaultdict(lambda: [0, 0.0])
        for d, c, s in items:
            key = reduce_to(d)
            agg[key][0] += c
            agg[key][1] += s
        for key, (c, s) in agg.items():
            out_rows.append((form, lemma, upos, feats_str(dict(key)), c, s))

    out_rows.sort(key=lambda r: (r[0].lower(), r[0], r[1], -r[4]))
    with open(f"it_{name}_ud.tsv", "w", encoding="utf-8") as out, \
         open(f"it_{name}_ud.counts.tsv", "w", encoding="utf-8") as cnt:
        cnt.write("form\tlemma\tupos\tfeats\tcount\tshare\n")
        for form, lemma, upos, feats, c, s in out_rows:
            out.write(f"{form}\t{lemma}\t{upos}\t{feats}\n")
            cnt.write(f"{form}\t{lemma}\t{upos}\t{feats}\t{c}\t{min(s, 1.0):.3f}\n")

    sys.stderr.write(
        f"[{name}] {len(files)} files, {n_tok} tokens, {len(by_form)} wordforms\n"
        f"        analyses kept: {len(out_rows)}  "
        f"(dropped <{MIN_SHARE:.0%}: {n_dropped}, keys collapsed: {n_collapsed})\n")


def main():
    names = sys.argv[1:] or list(TREEBANKS)
    for name in names:
        extract(name, TREEBANKS[name])


if __name__ == "__main__":
    main()
