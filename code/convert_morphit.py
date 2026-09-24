#!/usr/bin/env python3
"""Convert the Morph-it! lexicon (v0.4.8) to a UD-compatible morphology lexicon.

Output: TSV with 4 columns  FORM <tab> LEMMA <tab> UPOS <tab> FEATS
        FEATS is a pipe-separated, alphabetically sorted list of Feature=Value
        pairs following the Universal Dependencies v2 guidelines (Italian).
        FEATS is '_' when there are no features.

Design choices (see README_UD.md for the rationale):
  * "Keep all analyses": one output row per input line; genuinely ambiguous
    Morph-it tags that UD splits into several categories (CON, WH, WH-CHE,
    DET-WH, PRO-WH) emit *several* rows.
  * Clitics attached to verbs in Morph-it (inf+pres+sene ...) are dropped:
    UD tokenises them separately. The host verb analysis is kept.
  * Preposition+article contractions (ARTPRE, and the ARTPRE forms that
    Morph-it filed under ART) are tagged ADP with no features: UD splits
    them into ADP+DET, which a flat form lexicon cannot represent.
"""
import sys
from collections import defaultdict

IN = sys.argv[1] if len(sys.argv) > 1 else "morph-it/morph-it_048.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "it_morphit_ud.tsv"
UNMAPPED = "unmapped.tsv"

GEN = {"m": "Masc", "f": "Fem"}
NUM = {"s": "Sing", "p": "Plur"}
MOOD = {"ind": "Ind", "sub": "Sub", "cond": "Cnd", "impr": "Imp"}
TENSE = {"pres": "Pres", "past": "Past", "impf": "Imp", "fut": "Fut"}

# clitic tokens that Morph-it may append to verb tags
CLITICS = set("""cela cele celi celo cene ci gli gliela gliele glieli glielo gliene
la le li lo mela mele meli melo mene mi ne sela sele seli selo sene si
tela tele teli telo tene ti vela vele veli velo vene vi""".split())

# prep+article contraction surface forms wrongly filed under ART in Morph-it
ARTPRE_FORMS = {"del", "dell'", "dei", "delle", "dello", "della"}
INDEF_ART_LEMMAS = {"un", "uno", "una", "un'"}
NEG_ADV_LEMMAS = {"non", "mica", "neanche", "nemmeno", "neppure"}


def feats(d):
    d = {k: v for k, v in d.items() if v}
    if not d:
        return "_"
    return "|".join(f"{k}={d[k]}" for k in sorted(d))


def parse_gn(tokens):
    """Pull gender/number out of a token list regardless of order."""
    g = n = ""
    for t in tokens:
        if t in GEN:
            g = GEN[t]
        elif t in NUM:
            n = NUM[t]
    return g, n


def convert_verb(upos, tag_rest):
    """tag_rest e.g. 'ind+past+3+p' or 'part+past+s+m' or 'inf+pres+sene'."""
    toks = [t for t in tag_rest.split("+") if t not in CLITICS]
    form = toks[0]
    if form == "past":  # Morph-it typo for 'part+past+...'
        form = toks[0] = "part"
    f = {}
    if form == "inf":
        f["VerbForm"] = "Inf"
    elif form == "ger":
        f["VerbForm"] = "Ger"
    elif form == "part":
        f["VerbForm"] = "Part"
        f["Tense"] = TENSE.get(toks[1], "")
        f["Gender"], f["Number"] = parse_gn(toks[2:])
    elif form in MOOD:
        f["VerbForm"] = "Fin"
        f["Mood"] = MOOD[form]
        f["Tense"] = TENSE.get(toks[1], "")
        for t in toks[2:]:
            if t in "123":
                f["Person"] = t
            elif t in NUM:
                f["Number"] = NUM[t]
    else:
        return None
    return [(upos, f)]


def normalize_lemma(form, lemma, tag):
    """Article lemmas follow the UD/ISDT convention: il (definite), uno (indefinite)."""
    head = tag.partition(":")[0]
    if head in ("ART-M", "ART-F") and form not in ARTPRE_FORMS \
            and lemma not in ARTPRE_FORMS:
        return "uno" if lemma in INDEF_ART_LEMMAS else "il"
    return lemma


def convert(form, lemma, tag):
    """Return list of (upos, feats_dict); [] if unmapped."""
    head, _, rest = tag.partition(":")

    # ---- verbs -----------------------------------------------------------
    if head in ("VER", "MOD", "CAU", "ASP"):
        return convert_verb("VERB", rest)
    if head == "AUX":
        return convert_verb("AUX", rest)

    # ---- open classes --------------------------------------------------
    if head == "ADJ":
        toks = rest.split("+")
        f = {}
        if "comp" in toks:
            f["Degree"] = "Cmp"
        elif "sup" in toks:
            f["Degree"] = "Abs"
        f["Gender"], f["Number"] = parse_gn(toks)
        return [("ADJ", f)]

    if head in ("NOUN-M", "NOUN-F"):
        g = "Masc" if head.endswith("M") else "Fem"
        _, n = parse_gn(rest.split("+"))
        return [("NOUN", {"Gender": g, "Number": n})]

    if head == "NPR":
        return [("PROPN", {})]
    if head == "ADV":
        if lemma in NEG_ADV_LEMMAS:
            return [("ADV", {"PronType": "Neg"})]
        return [("ADV", {})]
    if head == "INT":
        return [("INTJ", {})]

    # ---- numerals ------------------------------------------------------
    if head in ("DET-NUM-CARD", "PRO-NUM"):
        return [("NUM", {"NumType": "Card"})]

    # ---- articles ----------------------------------------------------
    if head in ("ART-M", "ART-F"):
        if form in ARTPRE_FORMS or lemma in ARTPRE_FORMS:
            return [("ADP", {})]
        g = "Masc" if head.endswith("M") else "Fem"
        _, n = parse_gn(rest.split("+"))
        definite = "Ind" if lemma in INDEF_ART_LEMMAS else "Def"
        return [("DET", {"PronType": "Art", "Definite": definite,
                         "Gender": g, "Number": n})]

    if head in ("ARTPRE-M", "ARTPRE-F"):
        return [("ADP", {})]

    # ---- determiners -------------------------------------------------
    if head.startswith("DET-"):
        g, n = parse_gn(rest.split("+"))
        base = {"Gender": g, "Number": n}
        kind = head[4:]
        if kind == "DEMO":
            return [("DET", {**base, "PronType": "Dem"})]
        if kind == "INDEF":
            return [("DET", {**base, "PronType": "Ind"})]
        if kind == "POSS":
            return [("DET", {**base, "PronType": "Prs", "Poss": "Yes"})]
        if kind == "WH":
            return [("DET", {**base, "PronType": "Int"}),
                    ("DET", {**base, "PronType": "Rel"})]

    # ---- pronouns ---------------------------------------------------
    if head.startswith("PRO-"):
        rest_toks = head.split("-")[1:]  # e.g. ['PERS','CLI','3','M','S']
        f = {}
        clitic = "CLI" in rest_toks
        kind = rest_toks[0]
        for t in rest_toks:
            if t in ("1", "2", "3"):
                f["Person"] = t
            elif t in ("M", "F"):
                f["Gender"] = GEN[t.lower()]
            elif t in ("S", "P"):
                f["Number"] = NUM[t.lower()]
        if clitic:
            f["Clitic"] = "Yes"
        if kind == "PERS":
            f["PronType"] = "Prs"
            return [("PRON", f)]
        if kind == "DEMO":
            f["PronType"] = "Dem"
            return [("PRON", f)]
        if kind == "INDEF":
            f["PronType"] = "Ind"
            return [("PRON", f)]
        if kind == "POSS":
            f["PronType"] = "Prs"
            f["Poss"] = "Yes"
            return [("PRON", f)]
        if kind == "WH":
            base = {k: v for k, v in f.items() if k != "PronType"}
            return [("PRON", {**base, "PronType": "Int"}),
                    ("PRON", {**base, "PronType": "Rel"})]

    # ---- function words -------------------------------------------
    if head == "PRE":
        return [("ADP", {})]
    if head == "CON":
        return [("CCONJ", {}), ("SCONJ", {})]
    if head == "WH":
        return [("ADV", {"PronType": "Int"}),
                ("ADV", {"PronType": "Rel"}),
                ("SCONJ", {})]
    if head == "WH-CHE":
        return [("SCONJ", {}), ("PRON", {"PronType": "Rel"})]
    if head in ("CE", "CI", "NE", "SI"):
        f = {"Clitic": "Yes", "PronType": "Prs"}
        if head == "SI":
            f["Person"] = "3"
        return [("PRON", f)]
    if head == "TALE":
        g, n = parse_gn(rest.split("+"))
        return [("DET", {"Gender": g, "Number": n, "PronType": "Ind"})]

    # ---- punctuation / symbols / abbreviations -------------------
    if head in ("PON", "SENT"):
        return [("PUNCT", {})]
    if head in ("SMI", "SYM"):
        return [("SYM", {})]
    if head == "ABL":
        return [("X", {"Abbr": "Yes"})]

    return []


# features to drop from an entry when the *same* FORM+LEMMA+UPOS carries both
# of their values with everything else held equal (invariant form: not annotated)
UNDERSPEC = [("Gender", ("Masc", "Fem")), ("Number", ("Sing", "Plur"))]


def collapse_underspecified(feat_dicts):
    """feat_dicts: list of dicts for one (FORM, LEMMA, UPOS) key.
    Returns a de-duplicated list with underspecified Gender/Number removed."""
    entries = {frozenset(d.items()) for d in feat_dicts}
    changed = True
    while changed:
        changed = False
        for feat, (va, vb) in UNDERSPEC:
            buckets = defaultdict(set)  # feats-minus-feat -> set of that feat's values
            for e in entries:
                d = dict(e)
                buckets[frozenset((k, v) for k, v in d.items() if k != feat)].add(
                    d.get(feat))
            for rest, vals in buckets.items():
                if va in vals and vb in vals:
                    # drop `feat` from every entry in this bucket
                    for e in list(entries):
                        d = dict(e)
                        if frozenset((k, v) for k, v in d.items() if k != feat) == rest:
                            entries.discard(e)
                            d.pop(feat, None)
                            entries.add(frozenset(d.items()))
                    changed = True
    return [dict(e) for e in entries]


def main():
    n_in = n_unmapped = 0
    # (form, lemma, upos) -> list of feat dicts
    table = defaultdict(list)
    with open(IN, encoding="latin-1") as fh, \
         open(UNMAPPED, "w", encoding="utf-8") as unm:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                parts = line.split()
            if len(parts) != 3:
                continue
            form, lemma, tag = parts
            n_in += 1
            analyses = convert(form, lemma, tag)
            lemma = normalize_lemma(form, lemma, tag)
            if not analyses:
                n_unmapped += 1
                unm.write(line + "\n")
                continue
            for upos, f in analyses:
                table[(form, lemma, upos)].append({k: v for k, v in f.items() if v})

    n_out = n_collapsed = 0
    with open(OUT, "w", encoding="utf-8") as out:
        for (form, lemma, upos), dicts in table.items():
            before = {frozenset(d.items()) for d in dicts}
            kept = collapse_underspecified(dicts)
            after = {frozenset(d.items()) for d in kept}
            if after != before:
                n_collapsed += 1
            for d in sorted(kept, key=lambda x: feats(x)):
                out.write("\t".join((form, lemma, upos, feats(d))) + "\n")
                n_out += 1

    sys.stderr.write(
        f"input lines:            {n_in}\n"
        f"output rows:            {n_out}\n"
        f"(form,lemma,upos) keys collapsed (underspec. Gender/Number removed): "
        f"{n_collapsed}\n"
        f"unmapped lines:         {n_unmapped}  -> {UNMAPPED}\n")


if __name__ == "__main__":
    main()
