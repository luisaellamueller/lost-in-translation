"""Numbers for Appendix A (official German justifications 2000-2025).

Reads the per-document scores written by scripts/score_historical_complexity.py
(data/processed/historical_complexity.json.gz) and the coverage audit
(data/processed/motion_coverage.json).

Run from the repository root:
    python scripts/historical_summary.py
Output: results/historical_summary.md
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from statistics import mean

PROC = Path("data/processed")
PERIODS = [
    (2000, 2004),
    (2005, 2009),
    (2010, 2014),
    (2015, 2019),
    (2020, 2024),
    (2025, 2025),
]
METRICS = [
    ("mean_sentence_words", "Words per sentence"),
    ("mean_content_word_zipf", "Content-word Zipf"),
    ("mattr_50", "MATTR50"),
    ("lix", "LIX"),
]


def main() -> None:
    hist = json.load(
        gzip.open(PROC / "historical_complexity.json.gz", "rt", encoding="utf-8")
    )
    recs = hist["records"]
    lines = [
        "# Appendix A: official German justifications 2000-2025",
        "",
        f"Documents scored: {len(recs):,}",
        "",
        "| Period | Documents | " + " | ".join(l for _, l in METRICS) + " |",
        "|---|---:|" + "---:|" * len(METRICS),
    ]
    for a, b in PERIODS:
        rows = [r["official"] for r in recs if a <= r["year"] <= b]
        cells = [
            f"{mean(v for r in rows if (v := r.get(k)) is not None):.2f}"
            for k, _ in METRICS
        ]
        lines.append(f"| {a}-{b} | {len(rows):,} | " + " | ".join(cells) + " |")

    by_year = {y["year"]: y["metrics"] for y in hist["years"]}
    lines += [
        "",
        "2025 vs 2024 (yearly mean, 95% bootstrap interval from score_historical_complexity.py):",
        "",
    ]
    for k, label in METRICS:
        m24, m25 = by_year[2024][k], by_year[2025][k]
        overlap = not (
            m25["bootstrap_mean_ci95"][0] > m24["bootstrap_mean_ci95"][1]
            or m25["bootstrap_mean_ci95"][1] < m24["bootstrap_mean_ci95"][0]
        )
        lines.append(
            f"- {label}: 2024 {m24['mean']:.2f} {[round(x, 2) for x in m24['bootstrap_mean_ci95']]}, "
            f"2025 {m25['mean']:.2f} {[round(x, 2) for x in m25['bootstrap_mean_ci95']]}; "
            f"intervals overlap: {overlap}"
        )

    cov = {
        y["year"]: y
        for y in json.loads(
            (PROC / "motion_coverage.json").read_text(encoding="utf-8")
        )["years"]
    }
    lines += ["", "Motions without a German justification:", ""]
    for y in (2000, 2025):
        c = cov[y]
        lines.append(
            f"- {y}: {c['de_records'] - c['de_with_justification']} of {c['de_records']} "
            f"({100 * (1 - c['de_with_justification'] / c['de_records']):.0f}%)"
        )
    Path("results").mkdir(exist_ok=True)
    Path("results/historical_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
