# Exploratory source–target syntax associations

259 completed triples. Existing German depth/distance/length results reproduced exactly (numeric tolerance).

French: fr_core_news_sm 3.8.0 (UD Sequoia). German: de_core_news_sm 3.8.0 (TIGER/Tiger2Dep). Different annotation schemes prevent interpreting raw cross-language depth gaps as structural preservation.

| Measure | Source–official r | Source–model r | Difference [95% exploratory CI] |
|---|---:|---:|---|
| mean_sentence_tree_depth (raw) | 0.529 | 0.694 | +0.165 [+0.086, +0.251] |
| mean_sentence_tree_depth (length_adjusted) | 0.264 | 0.435 | +0.171 [+0.039, +0.300] |
| mean_dependency_distance (raw) | 0.364 | 0.546 | +0.181 [+0.079, +0.283] |
| mean_dependency_distance (length_adjusted) | 0.235 | 0.312 | +0.078 [-0.041, +0.191] |
| relative_clauses_per_sentence (raw) | 0.361 | 0.439 | +0.078 [-0.057, +0.215] |
| relative_clauses_per_sentence (length_adjusted) | 0.326 | 0.342 | +0.016 [-0.135, +0.174] |

## Interpretation limits

- Correlations describe document-level covariation, not sentence-aligned syntactic equivalence or causality.
- Length adjustment removes a fitted linear association with mean sentence length separately in each version; it does not remove every confound.
- Relative-clause counts use dependency labels, not the existing relative-pronoun marker counts; parser conventions/errors may differ.
- Exploratory intervals resample paired documents within year; repeated authors and multiple comparisons are not accounted for.
- Automatic analyses require spot-checking; equal clause counts can conceal changed constructions or meanings.

## Assistant spot-checks

- 20173849: the French parser reports zero relative clauses despite the final sentence containing a relative clause introduced by dont. This is a false negative; do not treat these counts as gold-standard annotations.
- 20073700: dependency-based counting identifies both official German relative clauses, including the one missed by the existing POS-marker measure. These are distinct operationalizations, not interchangeable counts.
- These checks are illustrative, not an independent human audit.

Reproduce: `python scripts/compare_source_syntax.py` (install `requirements.txt`).
