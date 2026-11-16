# Similarity of official translations to machine output

French-authored sample, 259 completed pairs. chrF/BLEU: machine vs official German (sacrebleu, sentence level). 95% intervals: 2000 document bootstrap resamples, seed 47.

| Period | Texts | chrF | 95% CI | BLEU |
|---|---:|---:|---|---:|
| 2000-2004 | 49 | 57.3 | [55.8, 58.6] | 16.2 |
| 2005-2009 | 50 | 56.4 | [54.9, 57.9] | 17.4 |
| 2010-2014 | 50 | 55.9 | [54.6, 57.3] | 17.2 |
| 2015-2019 | 50 | 57.8 | [56.6, 59.0] | 18.6 |
| 2020-2022 | 30 | 59.1 | [57.4, 61.0] | 20.1 |
| 2023-2025 | 30 | 61.4 | [59.3, 63.4] | 24.2 |

Linear trend: +1.63 chrF per decade, 95% CI [+0.81, +2.45].

A rising similarity is consistent with increasing machine-translation use, but also with the model having seen recent official translations during training.
