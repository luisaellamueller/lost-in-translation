"""Explore historical change and source-property adjustment of the chrF trend.

Run from the repository root: python scripts/check_similarity_confounding.py
Uses the existing 259 completed pairs only. No causal identification of MT use.
OLS year coefficients are per decade. Paired author-cluster bootstrap intervals
resample authors and retain all their documents (2,000 draws, seed 50).
"""

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
SEED, RESAMPLES = 50, 2000


def read_index(path):
    with path.open(encoding="utf-8") as f:
        return {int(r["document_id"]): r for r in csv.DictReader(f)}


def coefficient(design, outcome, indices):
    """Fit OLS on a draw and return the year coefficient (second design column)."""
    x, y = design[indices], outcome[indices]
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError("Rank-deficient regression design")
    return float(np.linalg.lstsq(x, y, rcond=None)[0][1])


def main():
    syntax = json.loads((DATA / "source_syntax_comparison.json").read_text())["records"]
    counts = json.loads((DATA / "source_structure_comparison.json").read_text())[
        "analyses"
    ]["punctuation_and_lines"]["records"]
    counts = {r["document_id"]: r for r in counts}
    scores = read_index(ROOT / "results/similarity_over_time.csv")
    authors = read_index(DATA / "motion_author_language.csv")
    ids = [r["document_id"] for r in syntax]
    if len(set(ids)) != len(ids) or set(ids) != set(scores) or set(ids) != set(counts):
        raise ValueError("Samples do not match exactly")
    rows = []
    for r in syntax:
        key = r["document_id"]
        author = authors[key]["member_id"]
        if not author:
            raise ValueError(f"Missing author: {key}")
        if r["year"] != int(scores[key]["year"]):
            raise ValueError("Year mismatch")
        rows.append(
            {
                "document_id": key,
                "year": r["year"],
                "author": author,
                "chrf": float(scores[key]["chrf"]),
                **{
                    f"{v}_{m}": r[v][m]
                    for v in ["source", "official"]
                    for m in ["mean_sentence_words", "mean_sentence_tree_depth"]
                },
                **{
                    f"{v}_word_count": counts[key][v]["word_count"]
                    for v in ["source", "official"]
                },
            }
        )
    n = len(rows)
    years = np.array([r["year"] for r in rows])
    decade = (years - 2000) / 10
    base = np.column_stack([np.ones(n), decade])
    # Source-only covariates avoid conditioning on the official translation outcome.
    source_features = np.column_stack(
        [
            [r["source_mean_sentence_words"] for r in rows],
            [r["source_mean_sentence_tree_depth"] for r in rows],
            np.log([r["source_word_count"] for r in rows]),
        ]
    )
    source_features = (
        source_features - source_features.mean(axis=0)
    ) / source_features.std(axis=0)
    adjusted = np.column_stack([base, source_features])
    author_ids = np.array([r["author"] for r in rows])
    groups = [np.flatnonzero(author_ids == a) for a in sorted(set(author_ids))]
    rng = np.random.default_rng(SEED)
    draws = [
        np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        for _ in range(RESAMPLES)
    ]
    all_ids = np.arange(n)

    def estimate(design, outcome):
        boots = np.array([coefficient(design, outcome, i) for i in draws])
        return {
            "slope_per_decade": coefficient(design, outcome, all_ids),
            "author_bootstrap_95_ci": np.quantile(boots, [0.025, 0.975]).tolist(),
        }, boots

    y = np.array([r["chrf"] for r in rows])
    unadj, b0 = estimate(base, y)
    adj, b1 = estimate(adjusted, y)
    difference = {
        "slope_difference_adjusted_minus_unadjusted": adj["slope_per_decade"]
        - unadj["slope_per_decade"],
        "paired_author_bootstrap_95_ci": np.quantile(b1 - b0, [0.025, 0.975]).tolist(),
    }
    trends = {}
    for version in ["source", "official"]:
        for metric in ["mean_sentence_words", "mean_sentence_tree_depth", "word_count"]:
            key = f"{version}_{metric}"
            trends[key] = estimate(base, np.array([r[key] for r in rows]))[0]
    periods = []
    for lo, hi in [
        (2000, 2004),
        (2005, 2009),
        (2010, 2014),
        (2015, 2019),
        (2020, 2022),
        (2023, 2025),
    ]:
        subset = [r for r in rows if lo <= r["year"] <= hi]
        periods.append(
            {
                "period": f"{lo}-{hi}",
                "n": len(subset),
                **{
                    k: float(np.mean([r[k] for r in subset])) for k in ["chrf", *trends]
                },
            }
        )
    output = {
        "n": n,
        "authors": len(groups),
        "seed": SEED,
        "bootstrap_draws": RESAMPLES,
        "population": "Existing 259 completed French-author translation pairs, 2000–2025; not the full corpus.",
        "models": {
            "unadjusted": "chrF ~ intercept + (year-2000)/10",
            "adjusted": "chrF ~ intercept + (year-2000)/10 + French mean sentence words + French mean tree depth + log French document word count",
        },
        "uncertainty": "Percentile author-cluster bootstrap; authors sampled with replacement, all their documents retained. No multiplicity correction.",
        "unadjusted": unadj,
        "adjusted": adj,
        "change_in_year_coefficient": difference,
        "within_language_trends": trends,
        "period_means": periods,
        "limitations": [
            "Linear descriptive trends can conceal nonlinear changes.",
            "Changes describe this text sample, not French/German language evolution generally.",
            "Adjustment does not address topics, guidelines, parser errors, unmeasured source properties or model training overlap.",
            "Remaining year association does not identify MT use; source changes could themselves reflect changing writing tools.",
        ],
        "records": rows,
    }
    (DATA / "similarity_source_adjustment.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Exploratory historical context and source-adjusted similarity",
        "",
        output["population"],
        "",
        "OLS slopes per decade; 2,000 author-cluster bootstrap samples, seed 50. Source controls: mean sentence length, mean tree depth, log document word count. Source controls standardized; year in decades. Intervals are exploratory and not multiplicity-corrected.",
        "",
        "| chrF model | Year slope per decade | 95% author-bootstrap interval |",
        "|---|---:|---|",
    ]
    for label, s in [("Unadjusted", unadj), ("Adjusted for French source", adj)]:
        lo, hi = s["author_bootstrap_95_ci"]
        lines.append(
            f"| {label} | {s['slope_per_decade']:+.3f} | [{lo:+.3f}, {hi:+.3f}] |"
        )
    lines += [
        "",
        f"Paired change in coefficient: {difference}",
        "",
        "| Within-language metric | Change per decade | 95% author-bootstrap interval |",
        "|---|---:|---|",
    ]
    for name, s in trends.items():
        lo, hi = s["author_bootstrap_95_ci"]
        lines.append(
            f"| {name} | {s['slope_per_decade']:+.3f} | [{lo:+.3f}, {hi:+.3f}] |"
        )
    lines += [
        "",
        "## Period means (descriptive)",
        "",
        "| Period | n | French words/sentence | German words/sentence | French depth | German depth | chrF |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for p in periods:
        lines.append(
            f"| {p['period']} | {p['n']} | {p['source_mean_sentence_words']:.2f} | {p['official_mean_sentence_words']:.2f} | {p['source_mean_sentence_tree_depth']:.2f} | {p['official_mean_sentence_tree_depth']:.2f} | {p['chrf']:.2f} |"
        )
    lines += ["", "## Limits", ""] + ["- " + s for s in output["limitations"]]
    (ROOT / "results/similarity_source_adjustment.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
