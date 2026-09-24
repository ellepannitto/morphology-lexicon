"""List ISDT lexicon analyses (form, lemma, upos, feats) absent from Morph-it!.

status:
  form_absent      the form does not occur in Morph-it! at all
  analysis_absent  the form occurs, but not with this (lemma, upos, feats)
"""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

def read(path):
    with open(path, encoding="utf-8") as f:
        return [r for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)]

morphit = read(DATA / "it_morphit_ud.tsv")
full = {tuple(r[:4]) for r in morphit}
forms = {r[0] for r in morphit}
lower_forms = {r[0].lower() for r in morphit}

rows = read(DATA / "it_isdt_ud.counts.tsv")[1:]
out = []
for form, lemma, upos, feats, count, share in rows:
    if (form, lemma, upos, feats) in full:
        continue
    status = "analysis_absent" if form in forms else "form_absent"
    out.append((form, lemma, upos, feats, count, share, status))

out.sort(key=lambda r: (r[6], -int(r[4]), r[0]))
with open(DATA / "isdt_not_in_morphit.tsv", "w", encoding="utf-8") as f:
    f.write("form\tlemma\tupos\tfeats\tcount\tshare\tstatus\n")
    for r in out:
        f.write("\t".join(r) + "\n")

from collections import Counter
print(len(rows), "ISDT analyses;", len(out), "not in Morph-it")
print(Counter(r[6] for r in out))
print(Counter((r[6], r[2]) for r in out).most_common(15))
