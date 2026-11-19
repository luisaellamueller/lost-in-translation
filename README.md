# Lost in Translation? Machine Translation and Swiss Parliamentary Texts

[![tests](https://github.com/luisaellamueller/lost-in-translation/actions/workflows/tests.yml/badge.svg)](https://github.com/luisaellamueller/lost-in-translation/actions/workflows/tests.yml)

Project for *Essentials in Text and Speech Processing* (ETH Zürich, Fall Semester 2026)
by **Luisa Müller** and **Klara Kolarova**.

Swiss parliamentary texts are published in German, French and Italian. This project
asks what would change if official translations were replaced by unrevised machine
translation (MT). We translate the French justifications of federal motions into
German with an open-weight MT model (TranslateGemma 4B) and compare the output with
the official German translation of the same text.

## Research questions and main findings

| | Question | Finding (259 French-authored motions, 2000–2025) |
|---|---|---|
| RQ1 | How does MT output differ from official translations in linguistic complexity? | MT uses more common words (+0.12 Zipf) but builds harder sentences: longer (+1.1 words), more deeply nested (+0.28 levels), with 15% more subordinate and 27% more relative clause markers; LIX +1.8. |
| RQ2 | Does MT respect Swiss conventions and parliamentary terminology? | No. It writes *ß* in 193 of 259 texts (official: 0), uses German number and quotation formats, renders *Interpellation* as *Anfrage* (12 of 15) and *Motion* as *Antrag* (18 of 43), and keeps French abbreviations (*AVS* for *AHV*) in 41 of 54 texts. |
| RQ3 | Have official translations become more similar to MT output over time? | Yes, since about 2015: chrF rises from 55.9 (2010–2014) to 61.4 (2023–2025). Surface errors of unrevised MT (*ß*) do not appear in official translations (0 of 435 in 2023–2025). |

The full report is submitted separately as a PDF. `docs/report_numbers.md` lists, for
every number in the report, the script and output file that produce it.

## Repository structure

```
data/raw/                 Curia Vista API snapshots (motions 2000–2025, DE and FR)
data/raw/author_api/      API snapshot of motion authors and members (author language)
data/processed/           cleaned corpus, sample, machine translations, measurements
scripts/                  all code (see table below)
results/                  tables written by the scripts (Markdown / CSV)
docs/figures/             figures used in the report
docs/report_numbers.md    which script produces which number in the report
docs/methods_log.md       development log, including abandoned approaches
tests/                    unit and regression tests (pytest)
.github/workflows/        continuous integration (see Quality assurance)
reproduce.sh              reruns every analysis in the report
```

## Setup

Tested with Python 3.14.7 on Apple Silicon macOS (direct dependency versions in
`environment_versions.json`).

```bash
git clone https://github.com/luisaellamueller/lost-in-translation.git
cd lost-in-translation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Reproduce all results

```bash
bash reproduce.sh            # offline, from the data in the repository (a few minutes)
bash reproduce.sh --fetch    # also re-downloads the author data from the Parliament API
```

This recomputes every number, table and figure in the report from the committed data.
It does not regenerate the machine translations (see below).

| Step | Script | What it does |
|---|---|---|
| Corpus | `audit_motion_coverage.py`, `check_data.py` | builds the corpus of 10,573 German–French motion justifications (2000–2025) and runs 32 consistency checks |
| Author language | `author_language_corpus.py` | infers the language each motion was written in from the submitting member (canton; biography language for bilingual cantons); 2,245 French-authored pairs |
| Sample | `prepare_french_sample.py` | 10 French-authored motions per year (260), seed 48; `--check` verifies the saved sample |
| Translation | `translate_pilot.py` | TranslateGemma 4B, temperature 0, seed 42 (259 completed, 1 output-limit failure) |
| RQ1 | `compare_expanded.py --french`, `report_rq1.py` | 18 complexity measures (spaCy `de_core_news_sm`, wordfreq), paired bootstrap; Figure 2 |
| RQ1 exploratory | `compare_source_structure.py`, `compare_source_syntax.py` | French-source sentence-count matching and depth correlations; length-adjusted correlations and year-stratified paired bootstrap |
| RQ2 | `swiss_conventions.py --french`, `terminology_check.py`, `screen_translations.py` | Swiss conventions, Table 1 (terminology), screening of the outputs |
| RQ3 | `similarity_over_time.py`, `special_characters.py` | chrF/BLEU over time (Figure 3); *ß* and dashes, Table 2 |
| Appendix | `score_historical_complexity.py`, `historical_summary.py` | complexity of all 10,581 official German texts, 2000–2025 |

`score_historical_complexity.py` reparses all 10,581 texts (slow) and is not part of
`reproduce.sh`; its saved output is `data/processed/historical_complexity.json.gz`. To
redraw the appendix figure, unpack it first:
`python -c "import gzip,shutil; shutil.copyfileobj(gzip.open('data/processed/historical_complexity.json.gz'), open('data/processed/historical_complexity.json','wb'))"`.

### Regenerating the machine translations (optional)

The translations are saved in `data/processed/complexity_fr_author_translations.json`.
To regenerate them (about 2 hours on an Apple M-series laptop):

```bash
python -m pip install -r requirements-translation.txt
mkdir -p models
# download translategemma-4b-it-Q4_K_M.gguf from
# https://huggingface.co/Menterium/translategemma-4b-it-GGUF into models/, then check:
shasum -a 256 models/translategemma-4b-it-Q4_K_M.gguf
# e7d9523174272fca61264b339f06d10c6115426267bb0f752b0124084e487b8e
```

Then follow `docs/french_sample_howto.md`. Model weights are not redistributed here;
check the model's licence at its source.

## Quality assurance

Every push and pull request runs the GitHub Actions workflow
[`.github/workflows/tests.yml`](.github/workflows/tests.yml) on a fresh Linux machine
(Python 3.14). The badge at the top shows the status of the latest run.

| Stage | What is checked | How |
|---|---|---|
| 1. Data consistency | 32 checks of the corpus, raw API pages, historical scores, sample and translations (e.g. 10,573 pairs, 41 exclusions, no HTML left, German and French fields in the right language) | `scripts/check_data.py`, fails the run on any failed check |
| 2. Offline rerun | author language, sample, RQ1 table and Figure 2, terminology (Table 1), screening, special characters (Table 2), appendix numbers are recomputed from the committed data | the analysis scripts listed above |
| 3. Results unchanged | the rerun must reproduce the committed results byte for byte, so no result file can drift from its code | `git diff --exit-code -- results/` |
| 4. Unit tests | the rules behind the results: author-language inference, terminology matching, abbreviation rule, dash definition, Fisher test (against its formula and a simulation) | `tests/test_rules.py` |
| 5. Regression tests | the numbers printed in the report: 259 + 1 translations, reproducible sample, 10,573 and 2,245 pairs, every row of Table 1, *ß* in 193 vs 0 texts, RQ1 differences and intervals, p = 0.008, screening annotations covering the drawn sample | `tests/test_report_numbers.py` |

The spaCy complexity scoring and the chrF/BLEU similarity are not rerun in CI, because
they need the full parser installation; they run locally with `reproduce.sh`, and the
regression tests check their saved outputs. The human judgements of the screening
(`results/screening_annotations_french.csv`) cannot be recomputed; stage 5 checks that
they cover exactly the randomly drawn and automatically flagged texts.

Run the same checks locally:

```bash
python scripts/check_data.py
python -m pytest -q
bash reproduce.sh          # full pipeline including spaCy and chrF; ends with the tests
```

## Exploratory source-structure analysis

The two source-comparison scripts use the same 259 completed translations and the
existing sentence-boundary conventions. French parsing adds `fr_core_news_sm` 3.8.0
(in `requirements.txt`). Run both scripts after the existing German scoring:

```bash
python scripts/compare_source_structure.py
python scripts/compare_source_syntax.py
```

Outputs are `data/processed/source_structure_comparison.json` and
`source_syntax_comparison.json`, with readable summaries under `results/`.
Both scripts also run through `reproduce.sh`. German measurements are checked
against the saved primary analysis. French and German dependency schemes differ;
correlations describe document-level covariation, not aligned tree equivalence.
The outputs include sentence counts, depth, dependency distance and relative
clauses. Exploratory intervals are not corrected for repeated authors or multiple
comparisons. Report edits are managed separately by the authors.

## Development material (not used in the report)

Some files document earlier steps and are kept because later scripts reuse them:

- `complexity_expanded_*` (data/processed), `prepare_expanded_sample.py`,
  `docs/expanded_comparison.md`: the first sample of 260 motions regardless of author
  language. Most of these were German originals, so the model translated a translation
  back; this is why we switched to French-authored motions. `prepare_french_sample.py`
  reuses its 63 French-authored translations and its 30 development IDs, and
  `check_data.py` still checks it.
- `prepare_pilot.py`, `complexity_translations.json`, `complexity_validation_*`,
  `complexity_multimeasure_pilot.json`, `docs/complexity_pilot_review.md`: the
  10-document pilot and 20-document evaluation used to fix the complexity measures.
- `author_language.py`, `sample_author_language.csv`: author language for the first
  sample only; superseded by `author_language_corpus.py`.
- `explore_2025_shift.py`: exploration of the 2025 change in the historical series.
- `results/terminology_review_french.csv`: empty annotation sheet written by
  `swiss_conventions.py`; the terminology results are in `results/terminology_french.md`.

## Contributions

- **Klara Kolarova:** corpus retrieval and cleaning, complexity measures, historical
  analysis, first translation sample and translation pipeline.
- **Luisa Müller:** Literature Research, French-authored sample and author-language inference, RQ2 and RQ3
  analyses (conventions, terminology, screening, similarity over time), reproducibility
  scripts, report.

## Data

Motion texts and author information come from the open data service of the Swiss
Parliament (Curia Vista, `https://ws.parlament.ch/odata.svc/`), retrieved in
November 2026. We analyse the justification (`ReasonText`) of all motions
(BusinessType 5) submitted 2000–2025.

## Limitations

- One small open-weight model; the federal administration more likely uses commercial
  systems such as DeepL.
- The original language of a motion is inferred from its author (a proxy).
- Complexity measures are parser-based estimates, not reader tests.
- Translation quality is assessed only through the terminology check and a screening
  (automatic checks on all outputs, reading 20 randomly drawn texts).
- Rising similarity to MT may partly reflect recent official translations in the
  model's training data.
- Before 2023 the API stores special characters (guillemets, dashes, *œ*) as plain
  substitutes, so character-level comparisons use 2023–2025 only.

## Licence

The code, figures and derived results in this repository are released under the
[MIT License](LICENSE). The parliamentary texts in `data/` come from the Swiss
Parliament's open data service and remain subject to its terms of use; the
TranslateGemma model is subject to its own licence.
