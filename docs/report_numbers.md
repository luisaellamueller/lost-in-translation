# Where each number in the report comes from

Every number, table and figure in the report is produced by a script in `scripts/`.
`bash reproduce.sh` runs them all in order (add `--fetch` to re-download the author
data from the Parliament API). Only two inputs are not computed by code:

* the machine translations (`data/processed/complexity_fr_author_translations.json`),
  generated once with `scripts/translate_pilot.py` (TranslateGemma 4B, temperature 0,
  seed 42; see `docs/french_sample_howto.md`), and
* human judgements in `results/screening_annotations_french.csv` (reading the 20
  randomly drawn outputs and the automatically flagged ones). The script checks that
  they cover exactly the drawn and flagged texts and counts them.

| Report section | Number(s) | Script | Output |
|---|---|---|---|
| Abstract, 3 Corpus | 10,573 pairs; 41 excluded entries; 1 duplicate API record | `check_data.py` | console |
| 3 Original language | 473 of 475 members (biography check); 2,245 French-authored pairs | `author_language_corpus.py` | `results/author_language_summary.md`, `data/processed/french_authored_motions.csv`, `data/processed/motion_author_language.csv` |
| 3 Sample | 260 pairs, 10 per year, seed 48, 30 development texts excluded | `prepare_french_sample.py --check` | console (sample identical: True) |
| 3 Translation | 259 completed, 1 failure (output limit) | `compare_expanded.py --french` | `docs/french_author_comparison.md` |
| 4.1 RQ1, Figure 2 | +1.1 words, +0.28 levels, +15%, +27%, +0.12 Zipf (1.3x, 200 of 259), MATTR, LIX +1.8, periods, dependency distance and lexical density n.s. | `compare_expanded.py --french`, `report_rq1.py` | `results/rq1_complexity.md`, `docs/figures/paired_differences.png` |
| 3 Analysis, 4.1 RQ1 | 102 authors, 60 with several texts; mixed model with author random intercepts and Bonferroni correction: all seven differences non-zero | `author_robustness.py` | `results/author_robustness.md` |
| 4.2 RQ2 | ß in 193 texts; 10.000 34 vs 3; Swiss forms 32; quotation marks | `swiss_conventions.py --french` | `results/swiss_conventions_counts_french.md` |
| 4.2 Table 1 | terminology counts; abbreviations 41 of 54 | `terminology_check.py` | `results/terminology_french.md`, `results/terminology_checked_french.csv`, `results/terminology_contexts_french.csv` |
| 4.2 Screening | length ratios, flags, 10/5/5 reading sample | `screen_translations.py` | `results/screening_french.md` |
| 4.3 RQ3, Figure 3 | chrF 55.9 / 61.4, trend +1.6 [+0.8, +2.5], BLEU 17 to 24 | `similarity_over_time.py` | `results/similarity_over_time.md`, `docs/figures/similarity_over_time.png` |
| 4.3 footnote | 8,825 texts; oeuvre / œuvre / guillemets before and after 2023 | `special_characters.py` | `results/special_characters.md` |
| 4.3 Table 2 | 259/193/37; 435/0/91; German/Italian row; 14 ß texts, members, Fisher p; dashes 37 vs 8; dashes per year | `special_characters.py` | `results/special_characters.md` |
| Appendix A | 10,581 texts; 20.6 words; Zipf 4.02 to 4.07; 2025 vs 2024; 21% / 3% | `historical_summary.py` (scores from `score_historical_complexity.py`) | `results/historical_summary.md`, `docs/figures/historical_complexity.png` |
| Figure 1 | study design (diagram, no numbers computed) | — | `docs/figures/design_tikz.tex` |

## Exploratory source-structure comparison

| Number | Script | Output |
|---|---|---|
| Sentence-count matches: model 166/259, official 86/259; punctuation-only 164/86 | `compare_source_structure.py` | `results/source_structure_comparison.md` |
| Depth correlations: model .694, official .529; adjusted .435/.264; difference .171 [.039,.300] | `compare_source_syntax.py` | `results/source_syntax_comparison.md` |

These additions use the same completed sample; all reported German primary measures are verified against saved results. The source analysis is exploratory, not part of the original seven-measure correction.
