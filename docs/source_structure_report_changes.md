# Source-structure additions for the report

Applied to `report/main.tex`, extracted from the saved ZIP. If Overleaf is newer, copy only these passages into it.

## Methods: after Analysis

```latex
\paragraph{Exploratory source comparison.} For all 259 completed translations, we compared sentence counts with the French source using punctuation and line boundaries, with punctuation-only segmentation as a sensitivity check. We parsed French with spaCy \texttt{fr\_core\_news\_sm} (3.8.0) and computed document-level Pearson correlations between source and target mean dependency-tree depth. To account for sentence length, we also correlated residuals after separately regressing depth on mean sentence length in each version. Exploratory 95\% intervals for correlation differences use 2,000 paired bootstrap resamples within year; unlike the primary analysis, they are not adjusted for repeated authors or multiple comparisons.
```

## Results: end of RQ1

```latex
\paragraph{Source-structure preservation.} The model matched the French source's sentence count in 166 of 259 texts (64\%), compared with 86 (33\%) for official translations; the pattern persisted with punctuation-only segmentation (164 versus 86). Source and target mean tree depth correlated more strongly for model translations ($r=0.69$) than official translations ($r=0.53$). After adjustment for sentence length, the correlations were 0.43 and 0.26, respectively (difference 0.17; exploratory 95\% CI [0.04, 0.30]). These findings are consistent with closer preservation of source structure, but do not establish matching sentence boundaries or syntactic constructions.
```

## Limitations: after the parser-based-measures sentence

French and German parsers use different annotation schemes, so the exploratory source comparison measures document-level covariation rather than directly equivalent dependency trees.
