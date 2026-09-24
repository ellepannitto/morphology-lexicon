"""Shared helpers for the Italian UD morphology-lexicon build."""
from collections import defaultdict

# features dropped from an entry when the *same* FORM+LEMMA+UPOS carries both
# of their values with everything else held equal (invariant form, not annotated)
UNDERSPEC = [("Gender", ("Masc", "Fem")), ("Number", ("Sing", "Plur"))]


def norm_feats(feats):
    """Sort a CoNLL-U FEATS string; '_' stays '_'."""
    if not feats or feats == "_":
        return "_"
    return "|".join(sorted(feats.split("|")))


def feats_str(d):
    """dict -> sorted 'A=x|B=y' string, or '_'."""
    d = {k: v for k, v in d.items() if v}
    if not d:
        return "_"
    return "|".join(f"{k}={d[k]}" for k in sorted(d))


def feats_to_dict(s):
    if not s or s == "_":
        return {}
    return dict(kv.split("=", 1) for kv in s.split("|"))


def collapse_underspecified(feat_dicts):
    """feat_dicts: list of dicts for one (FORM, LEMMA, UPOS) key.
    Merge entries that differ only by Gender Masc/Fem or Number Sing/Plur,
    dropping that feature. Applied to fixpoint. Returns a de-duplicated list."""
    entries = {frozenset(d.items()) for d in feat_dicts}
    changed = True
    while changed:
        changed = False
        for feat, (va, vb) in UNDERSPEC:
            buckets = defaultdict(set)  # feats-minus-feat -> set of that feat's values
            for e in entries:
                d = dict(e)
                rest = frozenset((k, v) for k, v in d.items() if k != feat)
                buckets[rest].add(d.get(feat))
            for rest, vals in buckets.items():
                if va in vals and vb in vals:
                    for e in list(entries):
                        d = dict(e)
                        if frozenset((k, v) for k, v in d.items()
                                     if k != feat) == rest:
                            entries.discard(e)
                            d.pop(feat, None)
                            entries.add(frozenset(d.items()))
                    changed = True
    return [dict(e) for e in entries]


def iter_conllu_tokens(path):
    """Yield (form, lemma, upos, feats_raw) for real tokens; skip comments,
    multiword-token ranges (2-3) and empty nodes (2.1)."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            col = line.split("\t")
            if len(col) != 10:
                continue
            idx = col[0]
            if "-" in idx or "." in idx:
                continue
            yield col[1], col[2], col[3], col[5]
