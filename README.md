# Italian UD-compatible morphology lexicon

Harmonised full-form lexicon for Italian, aligned to
[Universal Dependencies v2](https://universaldependencies.org/) (UPOS + FEATS),
following the conventions of the Italian UD treebanks (ISDT).

## Files

| file | description |
|---|---|
| `udlex.py` | shared helpers (FEATS normalisation, Gender/Number collapse, CoNLL-U reader) |
| `convert_morphit.py` | Morph-it! 0.4.8 → UD converter |
| `it_morphit_ud.tsv` | Morph-it converted lexicon: `FORM LEMMA UPOS FEATS` |
| `extract_ud.py` | UD treebank → lexicon extractor (used here for ISDT) |
| `it_isdt_ud.tsv` | ISDT lexicon, same 4-column format |
| `it_isdt_ud.counts.tsv` | each kept ISDT analysis with corpus `count` and `share` |
| `isdt_not_in_morphit.py` | lists ISDT analyses absent from the Morph-it lexicon |
| `isdt_not_in_morphit.tsv` | output of the above |

Inputs: upstream Morph-it! 0.4.8 in `morph-it/` (CC-BY-SA 2.0, Baroni &
Zanchetta), included in this repository, and the `UD_Italian-ISDT/` treebank
clone (CC-BY-NC-SA 3.0), not tracked here.

**Rebuild order:** `convert_morphit.py` → `extract_ud.py` → `isdt_not_in_morphit.py`

## Format

Tab-separated, 4 columns, UTF-8:

```
FORM <tab> LEMMA <tab> UPOS <tab> FEATS
```

* `FEATS` is a `|`-separated, **alphabetically sorted** list of `Feature=Value`
  pairs (UD v2), or `_` when empty.
* **All analyses are kept.** One row per Morph-it line; rows identical in all
  four columns are deduplicated. Morph-it tags that UD splits across several
  categories produce several rows (see below).

Run: `python3 convert_morphit.py [infile] [outfile]`

## Morph-it! → UD mapping

### Verbs — `VER`, `MOD`, `CAU`, `ASP` → `VERB`; `AUX` → `AUX`

| Morph-it | UD FEATS |
|---|---|
| `inf+pres` | `VerbForm=Inf` |
| `ger+pres` | `VerbForm=Ger` |
| `part+pres+<n>+<g>` | `VerbForm=Part\|Tense=Pres\|Gender\|Number` |
| `part+past+<n>+<g>` | `VerbForm=Part\|Tense=Past\|Gender\|Number` |
| `ind/sub/cond/impr + pres/past/impf/fut + <p> + <n>` | `VerbForm=Fin\|Mood\|Tense\|Person\|Number` |

Mood: `ind→Ind`, `sub→Sub`, `cond→Cnd`, `impr→Imp`.
Tense: `pres→Pres`, `past→Past` (passato remoto), `impf→Imp`, `fut→Fut`.
`cond` is always `Tense=Pres`.

**Clitics** appended by Morph-it (`inf+pres+sene`, `impr+pres+2+s+lo`, …) are
**dropped**: UD tokenises enclitic pronouns as separate words. The host-verb
analysis is kept; the lemma is left as Morph-it gives it (so inherently
pronominal verbs keep e.g. `accorgersi`). `VER:past+past+…` (a Morph-it typo)
is read as `part+past`.

### Nominals

| Morph-it | UD |
|---|---|
| `NOUN-M` / `NOUN-F` `:s/p` | `NOUN` + `Gender=Masc/Fem` + `Number` |
| `NPR` | `PROPN` |
| `ADJ:pos+<g>+<n>` | `ADJ` + `Gender` + `Number` |
| `ADJ:comp+…` | `ADJ` + `Degree=Cmp` + `Gender` + `Number` |
| `ADJ:sup+…` | `ADJ` + `Degree=Abs` + `Gender` + `Number` (superlativo assoluto) |
| `ADV` | `ADV` (`PronType=Neg` for `non`, `mica`, `neanche`, `nemmeno`, `neppure`) |
| `INT` | `INTJ` |

`Degree` is not emitted for the positive (UD Italian convention).

### Underspecified Gender / Number are removed

Morph-it enumerates every gender/number combination even for invariant forms
(`abbondante` → one `ADJ Gender=Masc|Number=Sing` row *and* one
`ADJ Gender=Fem|Number=Sing` row). After conversion, for each
`(FORM, LEMMA, UPOS)` key, if two entries are identical except that one has
`Gender=Masc` and the other `Gender=Fem` (or `Number=Sing` / `Number=Plur`),
they are merged into a single entry with that feature dropped — the form does
not mark the distinction. This cascades (`blu`: 4 rows → bare `ADJ`) and is
applied to fixpoint. 20,621 keys were collapsed; output went 504k → 482k rows.

It only fires when **one surface form** carries both values, i.e. genuine
invariance. A form that is only ever masc/sing (`andato`) keeps its features;
a common-gender noun attested in only one gender (`abruzzese`/`abruzzesi`)
is *not* caught here (Morph-it has a single gender value for that form).

### Determiners / pronouns

| Morph-it | UD |
|---|---|
| `ART-*` (true articles `il, la, un, …`) | `DET` `PronType=Art` `Definite=Def/Ind` `Gender` `Number`, lemma `il` / `uno` |
| `DET-DEMO` / `PRO-DEMO` | `DET`/`PRON` `PronType=Dem` |
| `DET-INDEF` / `PRO-INDEF` | `DET`/`PRON` `PronType=Ind` |
| `DET-POSS` / `PRO-POSS` | `DET`/`PRON` `PronType=Prs` `Poss=Yes` |
| `DET-WH` / `PRO-WH` | **two rows**: `PronType=Int` and `PronType=Rel` |
| `DET-NUM-CARD` / `PRO-NUM` | `NUM` `NumType=Card` |
| `PRO-PERS[-CLI]-<p>-<g>-<n>` | `PRON` `PronType=Prs` (+ `Clitic=Yes`, `Person`, `Gender`, `Number`) |
| `TALE` | `DET` `PronType=Ind` `Gender` `Number` |
| `NE`, `CI`, `CE` | `PRON` `Clitic=Yes` `PronType=Prs` |
| `SI` | `PRON` `Clitic=Yes` `PronType=Prs` `Person=3` |

`Definite=Ind` is assigned when the Morph-it lemma is `un/uno/una/un'`, else `Def`.
Article lemmas are then normalised to the ISDT convention: `il` for all
definite forms (`il, lo, la, i, gli, le, l'`), `uno` for all indefinite forms
(`un, uno, una, un'`).

### Function words

| Morph-it | UD |
|---|---|
| `PRE` | `ADP` |
| `ARTPRE-*`, plus the prep+article forms Morph-it filed under `ART` (`del, dei, delle, dell', dello, della`) | `ADP`, **no features** |
| `CON` | **two rows**: `CCONJ` and `SCONJ` (Morph-it does not distinguish) |
| `WH` (`come, quando, dove, perché, …`) | **three rows**: `ADV PronType=Int`, `ADV PronType=Rel`, `SCONJ` |
| `WH-CHE` (`che`) | **two rows**: `SCONJ`, `PRON PronType=Rel` |
| `PON`, `SENT` | `PUNCT` |
| `SMI` (emoticons), `SYM` | `SYM` |
| `ABL` (abbreviations `a.C.`, `D.P.R.`, …) | `X` `Abbr=Yes` — **needs manual review** (UD keeps the POS of the expansion) |

## Known limitations / review candidates

1. **Prep+article contractions** (`della`, `nei`, …) are single tokens tagged
   `ADP`. UD splits them into `ADP` + `DET`; a flat form lexicon cannot encode
   that. Downstream a multiword-token table is needed.
2. **Invariable words carrying Gender/Number.** Mostly handled: the collapse
   step (see "Underspecified Gender / Number are removed") strips Gender/Number
   from `che`, `altrui`, `blu`, etc. whenever Morph-it lists both values for one
   form. It cannot fix a form Morph-it pins to a single value (common-gender
   nouns like `abruzzese`).
3. **`CON` / `WH` over-generation.** Emitting both `CCONJ`/`SCONJ` (and the
   `ADV`/`SCONJ` split for `WH`) is deliberate under "keep all analyses";
   disambiguation is left to the tagger. Produce a deduped variant if a
   single-analysis lexicon is wanted.
4. **`MOD`/`CAU`/`ASP` → `VERB`.** UD Italian is not fully consistent on modals;
   revisit if aligning to a specific treebank that tags them `AUX`.
5. **`ABL`** entries need the POS of their expansion.

## ISDT lexicon (`extract_ud.py`)

`it_isdt_ud.tsv` is in the same 4-column format. Every `*.conllu` split is
read, one entry per token; multiword-token ranges (`2-3 dalla`) and empty nodes
are skipped, so contractions contribute their split components (`da` ADP,
`il` DET). FEATS are re-sorted; XPOS is discarded.

Two normalisation steps, in order:

1. **Ambiguity filter.** The item is the wordform (case-sensitive, as written);
   an analysis = a distinct `FORM/LEMMA/UPOS/FEATS` tuple. For a form with >1
   analysis, any analysis attested in **< 10 %** of that form's tokens is
   dropped; single-analysis forms are always kept.
2. **Collapse underspecified Gender / Number** — the same rule applied to
   Morph-it (see above): per `(FORM, LEMMA, UPOS)`, entries differing only by
   `Gender=Masc`/`Fem` or `Number=Sing`/`Plur` are merged with that feature
   dropped.

`it_isdt_ud.counts.tsv` records the frequency and share of every kept analysis
(share is post-collapse, so summed).

| tokens | wordforms | analyses kept | dropped <10% | keys collapsed |
|---|---|---|---|---|
| 298,338 | 29,619 | 31,960 | 1,056 | 30 |

Notes:
* **Case-sensitive.** `Stato`/`stato`, `La`/`la` are separate items.
* ISDT uses the `ExtPos` MWE feature; those variants mostly fall <10 %.

## ISDT analyses not in Morph-it (`isdt_not_in_morphit.py`)

`isdt_not_in_morphit.tsv` lists every ISDT analysis whose exact
`FORM/LEMMA/UPOS/FEATS` is absent from `it_morphit_ud.tsv`, with the ISDT
`count` and `share`, sorted by `status` then descending count:

| status | meaning | rows |
|---|---|---|
| `form_absent` | the form does not occur in Morph-it at all (mostly `PROPN`, `NOUN`, `NUM`, `VERB`) | 8,746 |
| `analysis_absent` | the form occurs in Morph-it, but with a different lemma/UPOS/FEATS | 2,036 |

10,782 of 31,960 ISDT analyses are missing in total.

## Licensing

Everything in this repository is released under
[CC-BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) (see `LICENSE`),
**except the three ISDT-derived files**, which must stay under the licence of
their source:

| files | derived from | licence |
|---|---|---|
| `morph-it/` | Morph-it! 0.4.8 | CC-BY-SA 2.0 **or** LGPL (dual-licensed), © 2004-2007 Marco Baroni & Eros Zanchetta |
| `it_morphit_ud.tsv`, `*.py`, `README_UD.md`, `CITATION.cff` | Morph-it! / this project | CC-BY-SA 2.0 |
| `it_isdt_ud.tsv`, `it_isdt_ud.counts.tsv`, `isdt_not_in_morphit.tsv` | UD_Italian-ISDT | CC-BY-NC-SA 3.0 (non-commercial, research use), see `LICENSE-ISDT.txt` |

**Morph-it!** is dual-licensed under CC-BY-SA 2.0 and the GNU LGPL. You may
copy, distribute and adapt it, including commercially, provided that you credit
the authors, distribute derivative works under the same licence, and make the
licence terms clear to others. The full text is in
`morph-it/readme-morph-it.txt` (section "Licensing information") and on the
[Morph-it! page](https://docs.sslmit.unibo.it/doku.php?id=resources:morph-it#licensing_information).
Resource: http://sslmit.unibo.it/morphit.

**UD_Italian-ISDT** is CC-BY-NC-SA 3.0 and released "for research purposes
only"; its user agreement is reproduced in `LICENSE-ISDT.txt`. It requires
citing Bosco et al. (2013, below) and, for electronic publication, linking
http://medialab.di.unipi.it/wiki/ISDT/. A CC-BY-SA licence would remove its
non-commercial restriction, which the ISDT licence does not allow, so the
ISDT-derived files keep CC-BY-NC-SA 3.0. The two sets of files are kept
separate and are not merged into a single work.

## Citation

See `CITATION.cff`. Please also cite the sources:

* Baroni, M. & Zanchetta, E. *Morph-it! A free corpus-based morphological
  resource for the Italian language.* http://sslmit.unibo.it/morphit
* Bosco, C., Montemagni, S. & Simi, M. (2013). *Converting Italian Treebanks:
  Towards an Italian Stanford Dependency Treebank.* 7th Linguistic Annotation
  Workshop & Interoperability with Discourse, ACL, Sofia.
* UD Italian ISDT, https://github.com/UniversalDependencies/UD_Italian-ISDT
  (http://medialab.di.unipi.it/wiki/ISDT/)
