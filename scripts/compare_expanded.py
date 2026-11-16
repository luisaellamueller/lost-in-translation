import json
from pathlib import Path

import numpy as np

from compare_complexity import compare_complexity


def compare_expanded(
    project_dir: Path,
    pairs_name: str = "complexity_expanded_pairs.json",
    translations_name: str = "complexity_expanded_translations.json",
    results_name: str = "complexity_expanded_results.json",
    report_name: str = "expanded_comparison.md",
    title: str = "Expanded translation comparison",
) -> None:
    """Compare completed translations and report failures and paired uncertainty.

    Args:
        project_dir: Project directory containing the fixed sample and outputs.
        pairs_name, translations_name, results_name: files in data/processed.
        report_name: Markdown table written to docs/.
        title: Heading of the Markdown table.
        The defaults reproduce the original 260-document comparison exactly.
    """
    # Check that every selected document has exactly one preserved attempt
    processed = project_dir / "data/processed"
    sample = json.loads((processed / pairs_name).read_text(encoding="utf-8"))
    translations = json.loads((processed / translations_name).read_text(encoding="utf-8"))
    expected = {row["document_id"]: row for row in sample["records"]}
    attempts = translations["records"] + translations["failed_records"]
    ids = [row["document_id"] for row in attempts]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("Translation attempts do not match the complete fixed sample.")
    for row in attempts:
        if any(row[key] != value for key, value in expected[row["document_id"]].items()):
            raise ValueError(f"Input differs from the fixed sample: {row['document_id']}")

    # Keep the original failed attempts while explicitly analysing completed cases
    compare_complexity(
        project_dir,
        input_name=translations_name,
        output_name=results_name,
        completed_cases_only=True,
    )
    path = processed / results_name
    results = json.loads(path.read_text(encoding="utf-8"))
    rng = np.random.default_rng(47)

    # Resample document pairs within submission year to retain the sampling design
    for metric, summary in results["summary"].items():
        available = [row for row in results["records"]
                     if row["official"][metric] is not None and row["generated"][metric] is not None]
        bootstrap_sums = np.zeros(2000)
        for year in range(2000, 2026):
            differences = [row["generated"][metric] - row["official"][metric]
                           for row in available if expected[row["document_id"]]["year"] == year]
            if differences:
                bootstrap_sums += rng.choice(differences, size=(2000, len(differences)), replace=True).sum(axis=1)
        summary["paired_bootstrap_ci95"] = np.quantile(bootstrap_sums / len(available), [0.025, 0.975]).tolist()

    # Save all measures and a readable comparison table
    results["uncertainty"] = "2000 paired-document bootstrap resamples within submission year, seed 47; observed complete-pair counts retained per year/metric. Percentile intervals are exploratory, without multiplicity correction; they do not capture generation-failure selection, author dependence, semantic errors or parser validity."
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# {title}", "",
        f"Attempted: {results['attempted_count']}; normally stopped outputs analysed: {results['completed_count']}; flagged failures excluded: {len(results['excluded_failures'])}.", "",
        "This is a completed-case analysis. Normal stopping is not evidence of semantic quality. Output-quality screening remains pending. The original translation file and failed output are unchanged.", "",
        "Differences are generated German minus official German. Intervals resample document pairs within submission year (2,000 resamples, seed 47); they are exploratory, not adjusted for testing multiple measures.", "",
        "| Measure | Pairs | Official mean | Generated mean | Difference | 95% paired interval | Higher / lower / tied |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for metric, summary in results["summary"].items():
        low, high = summary["paired_bootstrap_ci95"]
        lines.append(f"| {metric} | {summary['paired_count']} | {summary['official_mean']:.4f} | {summary['generated_mean']:.4f} | {summary['mean_difference']:+.4f} | [{low:+.4f}, {high:+.4f}] | {summary['generated_higher']} / {summary['generated_lower']} / {summary['ties']} |")
    lines.extend(["", "Excluded generation failures (full attempts remain in the input file):"])
    lines.extend(f"- {row['document_id']}: {row['finish_reason']}." for row in results["excluded_failures"])
    (project_dir / "docs" / report_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved completed-case results ({results_name}) and docs/{report_name}")


if __name__ == "__main__":
    # Run the comparison without regenerating translations.
    #   python scripts/compare_expanded.py           original 260-document sample
    #   python scripts/compare_expanded.py --french  French-authored sample
    import sys
    root = Path(__file__).resolve().parents[1]
    if "--french" in sys.argv:
        compare_expanded(root, pairs_name="complexity_fr_author_pairs.json",
                         translations_name="complexity_fr_author_translations.json",
                         results_name="complexity_fr_author_results.json",
                         report_name="french_author_comparison.md",
                         title="French-authored sample: machine vs official German")
    else:
        compare_expanded(root)
