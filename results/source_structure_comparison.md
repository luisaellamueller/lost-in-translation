# Exploratory source-structure comparison

259 completed French-source / official-German / generated-German triples. No new translations.

Counts use language-specific spaCy tokenizers, .!? sentence boundaries, preserved Art./art. and digit-letter references. The primary analysis also starts sentences at nonempty lines, as in the existing German analysis.

Negative paired gap differences mean the generated sentence count is closer to the source.

## punctuation_and_lines

| Measure | French | Official German | Generated German |
|---|---:|---:|---:|
| mean_sentence_count | 10.830 | 11.436 | 10.625 |
| mean_word_count | 289.541 | 245.892 | 237.185 |
| mean_sentence_words | 27.943 | 22.079 | 23.157 |
| exact_source_count_matches | — | 86.000 | 166.000 |
| mean_absolute_sentence_count_gap | — | 1.417 | 0.614 |
| mean_target_source_word_ratio | — | 0.856 | 0.823 |

Generated closer: 137; official closer: 32; tied: 90.
Paired mean absolute count-gap difference: -0.803; exploratory 95% bootstrap CI: [-0.9885135135135136, -0.6332046332046332].

## punctuation_only

| Measure | French | Official German | Generated German |
|---|---:|---:|---:|
| mean_sentence_count | 10.467 | 11.112 | 10.270 |
| mean_word_count | 289.541 | 245.892 | 237.185 |
| mean_sentence_words | 28.629 | 22.658 | 23.900 |
| exact_source_count_matches | — | 86.000 | 164.000 |
| mean_absolute_sentence_count_gap | — | 1.363 | 0.629 |
| mean_target_source_word_ratio | — | 0.856 | 0.823 |

Generated closer: 134; official closer: 35; tied: 90.
Paired mean absolute count-gap difference: -0.734; exploratory 95% bootstrap CI: [-0.9074324324324324, -0.5675675675675675].

## Validation and limits

German count differences against saved results: 0.

- Sentence-count equality does not establish matching boundaries, alignment, syntax or meaning.
- Language-specific tokenization and German compounding limit direct word-length comparisons.
- Rule-based segmentation can mishandle abbreviations and numbered lists.
- Bootstrap is exploratory, stratified by year, not adjusted for repeated authors or multiple testing.

## Inspected examples

- 20003048: French and generated German have 8 sentences; official German has 7. The official text combines the first two French sentences; the generated text keeps them separate.
- 20173849: French and generated German have 5 sentences; official German has 6. The official text separates the final reason into a sentence beginning Denn; the generated text keeps a da-clause.
- 20013149: French and generated German have 4 sentences; official German has 5. The official text splits the first French sentence. The generated text also contains meaning/grammar problems: matching sentence count is not a quality guarantee.

These are assistant spot-checks, not an independent human annotation study or a full boundary-alignment audit. Full segmented texts are in the JSON output.

Reproduce from the project root: `python scripts/compare_source_structure.py`.
