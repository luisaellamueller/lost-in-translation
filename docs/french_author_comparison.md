# French-authored sample: machine vs official German

Attempted: 260; normally stopped outputs analysed: 259; flagged failures excluded: 1.

This is a completed-case analysis. Normal stopping is not evidence of semantic quality. Output-quality screening remains pending. The original translation file and failed output are unchanged.

Differences are generated German minus official German. Intervals resample document pairs within submission year (2,000 resamples, seed 47); they are exploratory, not adjusted for testing multiple measures.

| Measure | Pairs | Official mean | Generated mean | Difference | 95% paired interval | Higher / lower / tied |
|---|---:|---:|---:|---:|---|---|
| word_count | 259 | 245.8919 | 237.1853 | -8.7066 | [-11.2241, -6.2199] | 78 / 176 / 5 |
| sentence_count | 259 | 11.4363 | 10.6255 | -0.8108 | [-1.0039, -0.6255] | 38 / 133 / 88 |
| mean_sentence_words | 259 | 22.0794 | 23.1575 | +1.0781 | [+0.6463, +1.5127] | 144 / 113 / 2 |
| mean_sentence_tree_depth | 259 | 6.5280 | 6.8049 | +0.2769 | [+0.1822, +0.3733] | 159 / 94 / 6 |
| mean_dependency_distance | 259 | 3.1442 | 3.1464 | +0.0022 | [-0.0323, +0.0377] | 128 / 131 / 0 |
| mean_content_word_zipf | 259 | 4.1554 | 4.2730 | +0.1175 | [+0.0978, +0.1362] | 200 / 59 / 0 |
| mean_covered_content_word_zipf | 259 | 4.2905 | 4.3626 | +0.0721 | [+0.0559, +0.0876] | 182 / 77 / 0 |
| unlisted_content_word_percent | 259 | 3.1704 | 2.0600 | -1.1105 | [-1.4367, -0.7820] | 86 / 158 / 15 |
| alphabetic_word_count | 259 | 238.4942 | 230.5946 | -7.8996 | [-10.4907, -5.3894] | 80 / 175 / 4 |
| mean_word_characters | 259 | 6.4142 | 6.3783 | -0.0359 | [-0.0691, -0.0030] | 128 / 131 / 0 |
| long_word_percent | 259 | 38.6539 | 39.3319 | +0.6780 | [+0.2734, +1.1147] | 148 / 111 / 0 |
| lexical_density_percent | 259 | 52.1963 | 52.0790 | -0.1173 | [-0.4187, +0.1755] | 136 / 121 / 2 |
| mattr_25 | 258 | 0.8469 | 0.8422 | -0.0047 | [-0.0074, -0.0019] | 113 / 145 / 0 |
| mattr_50 | 257 | 0.7707 | 0.7615 | -0.0092 | [-0.0123, -0.0060] | 97 / 160 / 0 |
| subordinators_per_100_words | 259 | 1.7657 | 2.0295 | +0.2637 | [+0.1664, +0.3627] | 161 / 90 / 8 |
| relative_markers_per_100_words | 259 | 1.3369 | 1.6921 | +0.3552 | [+0.2474, +0.4589] | 175 / 79 / 5 |
| mean_base_noun_phrase_words | 259 | 1.9609 | 1.9883 | +0.0274 | [+0.0127, +0.0431] | 151 / 104 / 4 |
| lix | 259 | 60.0930 | 61.8670 | +1.7740 | [+1.1939, +2.3434] | 161 / 98 / 0 |

Excluded generation failures (full attempts remain in the input file):
- 20003342: length.
