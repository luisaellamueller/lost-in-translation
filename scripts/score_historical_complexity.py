import argparse
import gzip
import json
from importlib.metadata import version
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import spacy

from compare_complexity import load_parser, measure_text


def score_history(project_dir: Path) -> None:
    """Measure official German justifications and summarise each year.

    Args:
        project_dir: Project directory containing the audited motion corpus.
    """
    # Load eligible texts and the same parser used for paired comparisons
    processed = project_dir / "data/processed"
    corpus = json.loads((processed / "motion_corpus.json").read_text(encoding="utf-8"))
    if corpus["completed_through"] != 2025:
        raise ValueError("Complete the coverage audit before scoring history.")
    source = [row for row in corpus["records"] if not row["exclusion_de"]]
    nlp = load_parser([row["reference_de"] for row in source])
    records = []
    yearly = []
    rng = np.random.default_rng(46)

    # Parse full documents and retain year-level checkpoints
    for year in range(2000, 2026):
        rows = [row for row in source if row["year"] == year]
        measurements = []
        unique_measurements = []
        seen_texts = set()
        for row, doc in zip(
            rows, nlp.pipe([row["reference_de"] for row in rows], batch_size=16)
        ):
            measures = measure_text(doc)
            measurements.append(measures)
            if row["reference_de"] not in seen_texts:
                unique_measurements.append(measures)
                seen_texts.add(row["reference_de"])
            records.append(
                {"document_id": row["document_id"], "year": year, "official": measures}
            )

        # Report distributions and document-level uncertainty for fixed measures
        summary = {}
        for metric, value in measurements[0].items():
            if value is not None and not isinstance(value, (int, float)):
                continue
            values = [row[metric] for row in measurements if row[metric] is not None]
            unique_values = [
                row[metric] for row in unique_measurements if row[metric] is not None
            ]
            if not values:
                continue
            bootstrap_means = rng.choice(
                values, size=(2000, len(values)), replace=True
            ).mean(axis=1)
            summary[metric] = {
                "available_documents": len(values),
                "mean": mean(values),
                "median": median(values),
                "q25": float(np.quantile(values, 0.25)),
                "q75": float(np.quantile(values, 0.75)),
                "bootstrap_mean_ci95": np.quantile(
                    bootstrap_means, [0.025, 0.975]
                ).tolist(),
                "deduplicated_documents": len(unique_values),
                "deduplicated_mean": mean(unique_values),
            }
        yearly.append({"year": year, "documents": len(rows), "metrics": summary})
        output = {
            "input_file": "motion_corpus.json",
            "completed_through": year,
            "spacy_version": spacy.__version__,
            "parser": "de_core_news_sm",
            "parser_version": nlp.meta["version"],
            "wordfreq_version": version("wordfreq"),
            "method": "Same load_parser and measure_text functions as compare_complexity.py; full official German ReasonText; flagged administrative entries excluded; each document weighted equally.",
            "uncertainty": "2000 document bootstrap resamples per metric/year, seed 46. Descriptive corpus means are exact for included records; intervals describe hypothetical document resampling, not missing-archive or measurement uncertainty. Author/topic dependence is not modelled. Exact-text deduplicated means within each year are a separate sensitivity check.",
            "years": yearly,
            "records": records,
        }
        path = processed / "historical_complexity.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(path)
        print(f"Saved {year}: {len(rows)} documents", flush=True)


def plot_history(project_dir: Path) -> None:
    """Plot yearly means and exact-text deduplication sensitivity.

    Args:
        project_dir: Project directory containing completed historical scores.
    """
    # Show distinct dimensions without a composite complexity score
    path = project_dir / "data/processed/historical_complexity.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        with gzip.open(path.with_suffix(".json.gz"), "rt", encoding="utf-8") as f:
            data = json.load(f)
    if data["completed_through"] != 2025:
        raise ValueError("Complete all historical years before plotting.")
    metrics = {
        "mean_content_word_zipf": "Content-word frequency (Zipf)",
        "mattr_50": "Lexical diversity (MATTR, 50 words)",
        "subordinators_per_100_words": "Subordinators per 100 words",
        "relative_markers_per_100_words": "Relative markers per 100 words",
        "mean_sentence_words": "Words per sentence",
        "lix": "LIX readability proxy",
    }
    figure, axes = plt.subplots(3, 2, figsize=(11, 9))
    years = [row["year"] for row in data["years"]]
    for axis, (metric, label) in zip(axes.flat, metrics.items()):
        values = [row["metrics"][metric] for row in data["years"]]
        axis.plot(
            years,
            [row["mean"] for row in values],
            color="#21618c",
            label="All eligible motions",
        )
        axis.plot(
            years,
            [row["deduplicated_mean"] for row in values],
            color="#bf6516",
            linestyle="--",
            label="Unique texts within year",
        )
        axis.fill_between(
            years,
            [row["bootstrap_mean_ci95"][0] for row in values],
            [row["bootstrap_mean_ci95"][1] for row in values],
            color="#21618c",
            alpha=0.12,
        )
        axis.set_title(label, fontsize=11)
        axis.set_xticks([2000, 2005, 2010, 2015, 2020, 2025])
        axis.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    figure.suptitle("Official German motion justifications, 2000-2025", fontsize=15)
    figure.text(
        0.5,
        0.015,
        "Each document has equal weight. Shading: 95% document-bootstrap intervals; author/topic dependence is not modelled.\nDescriptive corpus comparison, not an estimate of an AI effect. Original submission languages are unverified.",
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.06, 1, 0.96))
    output_dir = project_dir / "docs/figures"
    output_dir.mkdir(exist_ok=True)
    figure.savefig(output_dir / "historical_complexity.png", dpi=180)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Score or plot historical German complexity."
    )
    parser.add_argument(
        "--plot-only",
        action="store_true",
        help="Redraw from saved scores without reparsing the corpus",
    )
    args = parser.parse_args()
    project_dir = Path(__file__).resolve().parents[1]
    if not args.plot_only:
        score_history(project_dir)
    plot_history(project_dir)
