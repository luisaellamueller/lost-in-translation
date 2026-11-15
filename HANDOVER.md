# Handover for Luisa

Snapshot: 15 November 2026. Submission deadline: 20 November 2026.
This document describes what has actually been done, not a completed final report.

## 1. Current question and purpose

How do the lexical and grammatical complexity profiles of machine-generated
German versions of French Curia Vista motion justifications differ from their
official German counterparts? A secondary descriptive analysis asks how the
complexity of official German justifications varies across 2000-2025.

Political information can be expressed with more familiar vocabulary while
retaining or increasing other grammatical features. We therefore examine
separate dimensions, not one overall complexity score. Complexity is not
translation quality, reader comprehension, or a cost-benefit measure of human
translation. Mixed effects are an answer, not a reason to select different metrics.

Call the comparison texts "official German versions". Original submission
language and human-only translation provenance have not been established.
French is the designated model input, not a verified original in every case.

## 2. What Klara has done so far

1. Explored sentiment preservation. Parliamentary questions/justifications and
   domain-mismatched sentiment tools made that approach unreliable. Sentiment
   and dictionary fine-tuning are no longer active tasks.
2. Piloted separate complexity measures on ten documents and evaluated them on
   twenty additional documents. Fixed the definitions before the expanded run.
3. Retrieved Curia Vista OData records for motions (`BusinessType=5`) submitted
   in 2000-2025 in German and French. The analysed section is full `ReasonText`
   (justification), not the motion demand or government response.
4. Preserved raw API response bytes, query URLs and UTC retrieval times. Cleaned
   HTML while retaining paragraph/list boundaries and paired languages by ID.
5. Audited missing fields, exact duplicate API records and administrative notices.
6. Selected ten new eligible pairs per year from sorted IDs using
   `random.Random(45)`, excluding the thirty previously examined documents. No
   sentiment, complexity, topic or minimum-length selection was used.
7. Translated the full French justifications without showing the model German
   references. All 260 inputs fit the existing 2,048-token input cap.
8. Finished 260 generation attempts: 259 stopped normally, one hit the output
   limit and showed repetition. Preserved all attempts and kept the failure
   separate. No expanded paired scores have yet been produced.
9. Scored 10,581 eligible official German justifications and produced annual
   summaries and a historical chart. Updated the methods log throughout.

## 3. Data accounting

| Stage | Count |
|---|---:|
| API rows returned per language | 11,551 |
| Unique motion IDs per language | 11,550 |
| Nonempty German justifications | 10,622 |
| German administrative exclusions | 41 |
| Eligible German historical texts | 10,581 |
| Eligible German-French pairs | 10,573 |
| Fixed translation sample | 260 |
| Normally stopped generation outputs | 259 |
| Flagged generation failures | 1 |

The API duplicated ID 20243206 identically in both languages in 2024. Raw copies
are preserved; the corpus counts that ID once. The 41 German exclusions consist
of 27 manually verified reference-only notices, nine oral-justification notices
and five punctuation/XXX placeholders. Exclusion reasons remain in the corpus.
Short substantive arguments were retained. Screening is documented, not a claim
that every corpus entry has been manually validated.

Different IDs sometimes contain identical German text: 246 groups / 316 extra
copies in the eligible historical corpus. The historical analysis reports a
within-year exact-text deduplication sensitivity. The selected 260 have no exact
German-text duplication within the sample or with the thirty earlier documents.

## 4. Translation system and failure

The model is **TranslateGemma 4B, Q4_K_M GGUF**, run through llama-cpp-python.
It is not Llama 3.1: `Llama` is the runtime class name. Settings are temperature
0, seed 42, repeat penalty 1.0, 4,096 context tokens, 1,800 maximum output tokens,
and the model's embedded translation prompt template (FR to DE).

Document **20013159** used 1,986 prompt tokens and exactly 1,800 output tokens.
Its output ends during repetition of an earlier passage; `finish_reason=length`.
It is in `failed_records`, not the 259 completed records. Raising the cap alone
has not been tested and is not assumed to fix repetition. There has been no
replacement sampling or successful retry. Do not score its partial text as a
complete translation or claim a 260-pair completed comparison.

A normal stop is only a generation status. The 259 outputs still need checks
for repetition, obvious truncation and other failures. This screening does not
amount to comprehensive semantic translation-quality validation.

## 5. Measures and implementation

Both analyses call the same functions in `compare_complexity.py`:

| Dimension | Operational measures |
|---|---|
| Length | Word count, sentence count, mean words per sentence |
| Dependency structure | Mean maximum sentence tree depth; mean dependency distance |
| Vocabulary familiarity | Mean content-word Zipf frequency; covered-only frequency; unlisted share |
| Word form | Mean alphabetic word length; share longer than six letters |
| Lexical variety | Lemma MATTR windows 25 and 50; lexical density |
| Grammatical markers | Subordinators and relative markers per 100 alphabetic words |
| Noun phrases | Mean base noun-chunk length (diagnostic; parsing concerns) |
| Readability proxy | LIX: alphabetic words/sentence + percentage of words over six letters |

spaCy uses `de_core_news_sm` with named-entity recognition disabled, punctuation
sentence boundaries plus nonempty-line boundaries, and legal-abbreviation rules.
Word counts include numbers but exclude punctuation and whitespace. Lexical
measures use alphabetic tokens. Frequency includes NOUN/VERB/ADJ/ADV, excluding
proper nouns. MATTR is unavailable when the text is shorter than its window;
missing values are not zeros. The code saves inspectable sentence/word details.

Marker counts are not validated clause counts or reader difficulty. Base noun
chunks are not complete nested noun phrases. Swiss spelling, compounds and
technical terms affect word-frequency coverage. Historical frequency uses one
fixed resource, not a contemporary frequency dictionary for every year.

## 6. What the results currently say

The earlier twenty-document sample had higher generated content-word frequency
in 18/20 pairs (mean difference +0.252 Zipf; covered-only +0.145, 17/20 higher).
Relative-marker density was higher in 17/20, with one tie. MATTR50 decreased in
13/20 with a modest mean difference around -0.009. Other dimensions were mixed.
These are preliminary results; do not present them as the 259-pair findings.

The historical analysis is complete. Comparing equally weighted annual means
for 2000-2004 and 2021-2025 gives roughly 262 versus 221 words per document,
20.59 versus 20.54 words per sentence, and MATTR50 0.7735 versus 0.7742. This is a
post-hoc descriptive period summary, not a fitted trend or causal estimate.
The annual series is more informative than these endpoints. Some measures
fluctuate and 2025 differs visibly from preceding years.

Historical summaries include mean, median, quartiles, metric-specific N,
within-year deduplicated means and 2,000 document-bootstrap resamples per
metric/year (seed 46). These intervals do not capture topic/author dependence,
parser error or missing-archive bias. MATTR50 is unavailable for 149 short texts.
Missing justification rates change over time (68/322 in 2000 versus 23/710 in
2025). Do not attribute historical change to AI, political polarisation or
translation practices without evidence.

## 7. What to do next

1. Screen the 259 outputs for repetition and obvious generation problems, without
   selecting cases based on the desired complexity result. Preserve flags and
   exclusion reasons. Inspect representative normal cases too.
2. Decide and document the failure policy: e.g. a clearly labelled completed-case
   analysis with the observed failure rate, or a separate systematic retry
   experiment. Preserve the failed attempt and distinguish retries from the
   original method. The current comparison guard needs an explicit change or a
   documented derived input before scoring the 259 completed cases.
3. Run paired complexity scoring with the fixed definitions. Report available
   pairs per measure. Add paired document bootstrap uncertainty and period
   robustness summaries; these are not yet implemented for the expanded sample.
4. Inspect transparently selected examples (large changes, typical changes,
   counterexamples), checking French and both German versions. Distinguish
   rephrasing, compound unpacking, omissions and pre-existing bilingual mismatch.
5. Luisa can work independently on the historical interpretation, measurement
   validity and literature while Klara handles the paired analysis. Coordinate
   changes to the shared measurement functions before either branch merges.
6. Write the report around the final question and evidence, not a diary of all
   abandoned approaches. Select a project licence and publish reproducible code
   as required by the class, after checking data/model terms.

## 8. Script map

| File | Role |
|---|---|
| `scripts/audit_motion_coverage.py` | Download/reuse yearly raw pages; clean and audit the corpus |
| `scripts/prepare_pilot.py` | Supplies `clean_text` to the audit; old pilot entry point is not used |
| `scripts/prepare_expanded_sample.py` | Rebuild the fixed ten-per-year sample; requires included pilot inputs for excluded IDs |
| `scripts/translate_pilot.py` | Full-section translation and resumable completed/failed outputs; use explicit filenames |
| `scripts/compare_complexity.py` | Shared parsing/measures and paired summaries; default is the ten-document pilot |
| `scripts/score_historical_complexity.py` | Historical scoring, yearly summaries and figure |

The two preliminary translation files remain because sample selection reads
them to exclude thirty IDs. Other obsolete sentiment, interpellation and quality
scripts are deliberately absent. `prepare_pilot.py` remains solely as an actual
import dependency; do not execute its old interpellation workflow.

## 9. Verification already performed

- Refreshed 2000 API fields match the earlier snapshots exactly; 2025 DE row
  count also matched an independent API count request.
- Every selected ID and input matches the corpus; ten pairs per year, no overlap
  with the thirty preliminary IDs. Exact model prompts are 109-1,986 tokens.
- Shared scoring reproduces all forty prior validation texts and all thirty
  previously evaluated official texts exactly.
- Historical IDs, yearly counts, alphanumeric text coverage, LIX arithmetic and
  MATTR bounds checked for all 10,581 documents.
- Mock-generation tests verified interrupted-run recovery, rejection of changed
  inputs, preservation of failed outputs and continuation after a length stop.
- Normally stopped outputs have NOT all been semantically evaluated.

## 10. Report and sources

The included class instructions require an English PDF of at most five content
pages, 11-point text and a link to reproducible open-source code. They do not
require proving human translation superior or submitting two notebooks.

Read `docs/complexity_pilot_review.md` for detailed findings and literature roles.
Read `docs/methods_log.md` for the unabridged chronology: earlier sections describe
superseded experiments and may reference files intentionally omitted from this
active-code handover. This handover's status takes precedence over older entries.

Relevant starting points (read before citing detailed claims):
- Vanmassenhove et al. (2021), Machine Translationese:
  https://aclanthology.org/2021.eacl-main.188/
- Tolochko et al. (2019), political text complexity and knowledge:
  https://doi.org/10.1080/10584609.2019.1631919
- Reveilhac and Schneider (2025), complexity in Swiss parliamentary debates:
  https://doi.org/10.1075/cilt.370.16rev
  Only its publisher abstract was checked earlier; the full chapter needs reading.

Nothing in the current results establishes that human translations are or are
not worth their cost. The defensible contribution is an auditable comparison of
linguistic profiles on matched parliamentary content, with explicit limitations.
