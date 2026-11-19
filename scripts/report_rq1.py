"""RQ1 numbers and Figure 2: machine minus official German, French-authored sample.

Reads the paired results written by
    python scripts/compare_expanded.py --french
and reports, for the seven measures used in the paper, the mean difference,
the difference as a percentage of the official mean, the 95% paired bootstrap
interval (from compare_expanded: 2,000 resamples within year, seed 47), the
number of pairs where the machine value is higher, and the direction of the
difference in three periods.

Run from the repository root:
    python scripts/report_rq1.py
Outputs: results/rq1_complexity.md, docs/figures/paired_differences.png
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROC = Path("data/processed")
MEASURES = [  # (key, label, group)
    ("mean_sentence_words", "Words per sentence", "Syntax"),
    ("mean_sentence_tree_depth", "Max. tree depth", "Syntax"),
    ("subordinators_per_100_words", "Subordinate clauses / 100 words", "Syntax"),
    ("relative_markers_per_100_words", "Relative clauses / 100 words", "Syntax"),
    ("mean_content_word_zipf", "Word frequency (Zipf)", "Vocabulary"),
    ("mattr_50", "Lexical variety (MATTR)", "Vocabulary"),
    ("lix", "Readability index (LIX)", "Readability"),
]
NOT_DIFFERENT = [
    ("mean_dependency_distance", "Mean dependency distance"),
    ("lexical_density_percent", "Lexical density"),
]
PERIODS = [(2000, 2008), (2009, 2016), (2017, 2025)]
COLOURS = {"Syntax": "#2a6f97", "Vocabulary": "#c26a1b", "Readability": "#444444"}


def as_dict(v):
    return v if isinstance(v, dict) else ast.literal_eval(v)


def main() -> None:
    res = json.loads(
        (PROC / "complexity_fr_author_results.json").read_text(encoding="utf-8")
    )
    year = {
        r["document_id"]: int(r["year"])
        for r in json.loads(
            (PROC / "complexity_fr_author_pairs.json").read_text(encoding="utf-8")
        )["records"]
    }
    recs = [
        (r["document_id"], as_dict(r["official"]), as_dict(r["generated"]))
        for r in res["records"]
    ]

    def diffs(key, ids=None):
        return [
            (g[key] - o[key], o[key])
            for d, o, g in recs
            if o.get(key) is not None
            and g.get(key) is not None
            and (ids is None or d in ids)
        ]

    lines = [
        "# RQ1: machine minus official German (French-authored sample)",
        "",
        f"Completed pairs: {len(recs)}. Interval: {res['uncertainty'].split(';')[0]}.",
        "",
        "| Measure | Pairs | Difference | % of official mean | 95% CI | % CI | Machine higher | "
        + " | ".join(f"{a}-{b}" for a, b in PERIODS)
        + " |",
        "|---|---:|---:|---:|---|---|---:|" + "---:|" * len(PERIODS),
    ]
    rows = []
    for key, label, group in MEASURES:
        d = diffs(key)
        diff, off = mean(x for x, _ in d), mean(o for _, o in d)
        lo, hi = res["summary"][key]["paired_bootstrap_ci95"]
        higher = sum(x > 0 for x, _ in d)
        per = []
        for a, b in PERIODS:
            ids = {k for k, y in year.items() if a <= y <= b}
            per.append(mean(x for x, _ in diffs(key, ids)))
        rows.append(
            (label, group, diff, 100 * diff / off, 100 * lo / off, 100 * hi / off)
        )
        lines.append(
            f"| {label} | {len(d)} | {diff:+.3f} | {100 * diff / off:+.1f}% | [{lo:+.3f}, {hi:+.3f}] | "
            f"[{100 * lo / off:+.1f}%, {100 * hi / off:+.1f}%] | {higher} of {len(d)} | "
            + " | ".join(f"{p:+.3f}" for p in per)
            + " |"
        )
    zipf = mean(x for x, _ in diffs("mean_content_word_zipf"))
    lines += [
        "",
        f"A Zipf difference of {zipf:+.3f} means content words are {10 ** zipf:.2f} times more frequent.",
        "",
        "Measures reported as not different (interval includes 0):",
    ]
    for key, label in NOT_DIFFERENT:
        lo, hi = res["summary"][key]["paired_bootstrap_ci95"]
        lines.append(
            f"- {label}: {mean(x for x, _ in diffs(key)):+.3f} [{lo:+.3f}, {hi:+.3f}]"
        )
    Path("results").mkdir(exist_ok=True)
    Path("results/rq1_complexity.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))

    # Separate the logarithmic Zipf score from relative changes in other measures.
    fig, (ax, az) = plt.subplots(
        2, 1, figsize=(6.8, 4.0), gridspec_kw={"height_ratios": [5, 1.2]}
    )
    plotted = [r for r in reversed(rows) if r[0] != "Word frequency (Zipf)"]
    for i, (label, group, diff, pct, plo, phi) in enumerate(plotted):
        c = COLOURS[group]
        ax.errorbar(
            pct, i, xerr=[[pct - plo], [phi - pct]], fmt="o", color=c, capsize=3, ms=5
        )
        ax.annotate(
            f"{diff:+.3f} ({pct:+.1f}%)",
            (phi, i),
            xytext=(5, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
        )
    ax.set_yticks(range(len(plotted)), [r[0] for r in plotted], fontsize=8)
    ax.set_xlim(-12, 54)
    ax.set_xlabel("Difference (% of official mean), 95% CI", fontsize=8)
    summary = res["summary"]["mean_content_word_zipf"]
    delta = summary["mean_difference"]
    low, high = summary["paired_bootstrap_ci95"]
    az.errorbar(
        delta,
        0,
        xerr=[[delta - low], [high - delta]],
        fmt="o",
        color=COLOURS["Vocabulary"],
        capsize=3,
        ms=5,
    )
    az.annotate(
        f"{delta:+.3f} Zipf",
        (high, 0),
        xytext=(5, 0),
        textcoords="offset points",
        va="center",
        fontsize=8,
    )
    az.set_yticks([0], ["Word frequency (Zipf)"], fontsize=8)
    az.set_xlim(-0.02, 0.21)
    az.set_ylim(-0.6, 0.6)
    az.set_xlabel("Difference (Zipf points), 95% CI", fontsize=8)
    for axis in (ax, az):
        axis.axvline(0, color="#999999", lw=0.8)
        axis.tick_params(axis="x", labelsize=8)
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
    fig.suptitle("Generated minus official German", fontsize=10)
    fig.tight_layout()
    Path("docs/figures").mkdir(parents=True, exist_ok=True)
    fig.savefig("docs/figures/paired_differences_zipf_units.png", dpi=300)
    print("Saved docs/figures/paired_differences_zipf_units.png")


if __name__ == "__main__":
    main()
