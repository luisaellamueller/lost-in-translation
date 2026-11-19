# Exploratory historical context and source-adjusted similarity

Existing 259 completed French-author translation pairs, 2000–2025; not the full corpus.

OLS slopes per decade; 2,000 author-cluster bootstrap samples, seed 50. Source controls: mean sentence length, mean tree depth, log document word count. Source controls standardized; year in decades. Intervals are exploratory and not multiplicity-corrected.

| chrF model | Year slope per decade | 95% author-bootstrap interval |
|---|---:|---|
| Unadjusted | +1.628 | [+0.697, +2.570] |
| Adjusted for French source | +1.711 | [+0.949, +2.506] |

Paired change in coefficient: {'slope_difference_adjusted_minus_unadjusted': 0.08259774633142736, 'paired_author_bootstrap_95_ci': [-0.5448452836992247, 0.6776364094954155]}

| Within-language metric | Change per decade | 95% author-bootstrap interval |
|---|---:|---|
| source_mean_sentence_words | -0.317 | [-1.513, +0.844] |
| source_mean_sentence_tree_depth | -0.014 | [-0.175, +0.163] |
| source_word_count | -33.451 | [-76.906, +4.841] |
| official_mean_sentence_words | +0.315 | [-0.391, +1.006] |
| official_mean_sentence_tree_depth | -0.039 | [-0.186, +0.113] |
| official_word_count | -27.392 | [-64.176, +4.934] |

## Period means (descriptive)

| Period | n | French words/sentence | German words/sentence | French depth | German depth | chrF |
|---|---:|---:|---:|---:|---:|---:|
| 2000-2004 | 49 | 28.51 | 21.70 | 5.58 | 6.56 | 57.27 |
| 2005-2009 | 50 | 27.66 | 21.43 | 5.44 | 6.55 | 56.41 |
| 2010-2014 | 50 | 27.56 | 22.06 | 5.31 | 6.42 | 55.94 |
| 2015-2019 | 50 | 28.27 | 23.11 | 5.64 | 6.71 | 57.79 |
| 2020-2022 | 30 | 28.11 | 23.11 | 5.66 | 6.39 | 59.15 |
| 2023-2025 | 30 | 27.41 | 21.09 | 5.33 | 6.44 | 61.37 |

## Limits

- Linear descriptive trends can conceal nonlinear changes.
- Changes describe this text sample, not French/German language evolution generally.
- Adjustment does not address topics, guidelines, parser errors, unmeasured source properties or model training overlap.
- Remaining year association does not identify MT use; source changes could themselves reflect changing writing tools.
