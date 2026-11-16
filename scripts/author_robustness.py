"""RQ1 robustness: does author dependence change the paired results?

Several motions in the sample were submitted by the same parliamentarian, so
document pairs are not fully independent. For each of the seven reported
measures we estimate the mean machine-minus-official difference in two ways
that account for this:
  1. a linear mixed-effects model, difference ~ 1 + (1 | author), fitted with
     statsmodels MixedLM (REML); the fixed intercept is the author-adjusted
     mean difference with its 95% Wald interval;
  2. a cluster bootstrap that resamples authors (2,000 resamples, seed 47).
The mixed-model intervals are also reported with a Bonferroni correction for
the seven measures (alpha = 0.05 / 7).

Run from the repository root (needs statsmodels):
    python scripts/author_robustness.py
Output: results/author_robustness.md
"""
from __future__ import annotations

import ast
import csv
import json
import random
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
import statsmodels.formula.api as smf

PROC = Path("data/processed")
MEASURES = [
    ("mean_sentence_words", "Words per sentence"),
    ("mean_sentence_tree_depth", "Max. tree depth"),
    ("subordinators_per_100_words", "Subordinate clauses / 100 words"),
    ("relative_markers_per_100_words", "Relative clauses / 100 words"),
    ("mean_content_word_zipf", "Word frequency (Zipf)"),
    ("mattr_50", "Lexical variety (MATTR)"),
    ("lix", "Readability index (LIX)"),
]
SEED, RESAMPLES = 47, 2000


def as_dict(v):
    return v if isinstance(v, dict) else ast.literal_eval(v)


def main() -> None:
    with open(PROC / "motion_author_language.csv", encoding="utf-8") as f:
        author = {int(r["document_id"]): r["member_id"] for r in csv.DictReader(f)}
    res = json.loads((PROC / "complexity_fr_author_results.json").read_text(encoding="utf-8"))
    recs = [(int(r["document_id"]), as_dict(r["official"]), as_dict(r["generated"])) for r in res["records"]]
    authors = Counter(author[d] for d, _, _ in recs)

    lines = ["# RQ1 robustness to author dependence", "",
             f"Pairs: {len(recs)}; distinct authors: {len(authors)}; authors with more than one text: "
             f"{sum(n > 1 for n in authors.values())}; most texts by one author: {max(authors.values())}.", "",
             "| Measure | Mean difference (document bootstrap, reported) | Mixed model: author-adjusted difference [95% CI] | "
             "Author cluster bootstrap [95% CI] | Mixed model, Bonferroni (7 measures) |",
             "|---|---|---|---|---|"]
    for key, label in MEASURES:
        rows = [(author[d], g[key] - o[key]) for d, o, g in recs
                if o.get(key) is not None and g.get(key) is not None]
        lo_d, hi_d = res["summary"][key]["paired_bootstrap_ci95"]
        data = {"diff": [x for _, x in rows], "author": [a for a, _ in rows]}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # boundary/convergence notes when author variance is ~0
            fit = smf.mixedlm("diff ~ 1", data, groups=data["author"]).fit(reml=True)
        est = fit.params["Intercept"]
        lo_m, hi_m = fit.conf_int().loc["Intercept"]
        lo_b, hi_b = fit.conf_int(alpha=0.05 / len(MEASURES)).loc["Intercept"]
        by_author = defaultdict(list)
        for a, x in rows:
            by_author[a].append(x)
        clusters = list(by_author.values())
        rng = random.Random(SEED)
        boots = sorted(mean(x for c in rng.choices(clusters, k=len(clusters)) for x in c) for _ in range(RESAMPLES))
        lo_c, hi_c = boots[int(0.025 * RESAMPLES) - 1], boots[int(0.975 * RESAMPLES)]
        lines.append(f"| {label} | {mean(x for _, x in rows):+.3f} [{lo_d:+.3f}, {hi_d:+.3f}] | "
                     f"{est:+.3f} [{lo_m:+.3f}, {hi_m:+.3f}] | {mean(x for _, x in rows):+.3f} [{lo_c:+.3f}, {hi_c:+.3f}] | "
                     f"[{lo_b:+.3f}, {hi_b:+.3f}] |")
    Path("results").mkdir(exist_ok=True)
    Path("results/author_robustness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
