# Expanded translation comparison

Attempted: 260; normally stopped outputs analysed: 259; flagged failures excluded: 1.

This is a completed-case analysis. Normal stopping is not evidence of semantic quality. Output-quality screening remains pending. The original translation file and failed output are unchanged.

Differences are generated German minus official German. Intervals resample document pairs within submission year (2,000 resamples, seed 47); they are exploratory, not adjusted for testing multiple measures.

| Measure | Pairs | Official mean | Generated mean | Difference | 95% paired interval | Higher / lower / tied |
|---|---:|---:|---:|---:|---|---|
| word_count | 259 | 220.6988 | 227.0270 | +6.3282 | [+3.0693, +9.4633] | 162 / 91 / 6 |
| sentence_count | 259 | 11.2780 | 10.7490 | -0.5290 | [-0.7490, -0.3126] | 51 / 100 / 108 |
| mean_sentence_words | 259 | 19.9203 | 21.5848 | +1.6645 | [+1.2468, +2.1175] | 180 / 75 / 4 |
| mean_sentence_tree_depth | 259 | 6.0775 | 6.5420 | +0.4646 | [+0.3575, +0.5743] | 175 / 75 / 9 |
| mean_dependency_distance | 259 | 3.0216 | 3.0687 | +0.0471 | [+0.0051, +0.0896] | 139 / 120 / 0 |
| mean_content_word_zipf | 259 | 4.0728 | 4.2686 | +0.1958 | [+0.1745, +0.2174] | 221 / 38 / 0 |
| mean_covered_content_word_zipf | 259 | 4.2475 | 4.3589 | +0.1114 | [+0.0933, +0.1298] | 197 / 62 / 0 |
| unlisted_content_word_percent | 259 | 4.1432 | 2.0698 | -2.0735 | [-2.4294, -1.7404] | 60 / 187 / 12 |
| alphabetic_word_count | 259 | 213.4363 | 221.0193 | +7.5830 | [+4.3050, +10.7763] | 171 / 85 / 3 |
| mean_word_characters | 259 | 6.5776 | 6.4451 | -0.1326 | [-0.1719, -0.0926] | 93 / 166 / 0 |
| long_word_percent | 259 | 40.2169 | 40.3429 | +0.1261 | [-0.3567, +0.6440] | 138 / 119 / 2 |
| lexical_density_percent | 259 | 53.9814 | 52.7454 | -1.2360 | [-1.5926, -0.8916] | 85 / 172 / 2 |
| mattr_25 | 258 | 0.8547 | 0.8445 | -0.0102 | [-0.0135, -0.0069] | 87 / 171 / 0 |
| mattr_50 | 256 | 0.7763 | 0.7631 | -0.0133 | [-0.0173, -0.0096] | 78 / 178 / 0 |
| subordinators_per_100_words | 259 | 1.5955 | 2.0844 | +0.4889 | [+0.3636, +0.6163] | 166 / 84 / 9 |
| relative_markers_per_100_words | 259 | 0.9653 | 1.5473 | +0.5820 | [+0.4666, +0.6972] | 183 / 63 / 13 |
| mean_base_noun_phrase_words | 259 | 1.9760 | 1.9929 | +0.0168 | [-0.0018, +0.0365] | 143 / 111 / 5 |
| lix | 259 | 59.5242 | 61.3989 | +1.8747 | [+1.3195, +2.4512] | 169 / 89 / 1 |

Excluded generation failures (full attempts remain in the input file):
- 20013159: length.
