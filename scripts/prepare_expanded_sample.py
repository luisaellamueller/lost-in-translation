import json
import random
from pathlib import Path


def prepare_sample(project_dir: Path) -> None:
    """Select ten new paired justifications per year without inspecting scores.

    Args:
        project_dir: Project directory containing the completed coverage audit.
    """
    # Exclude every document used to develop or inspect the earlier measures
    processed = project_dir / "data/processed"
    excluded_ids = set()
    for filename in (
        "complexity_translations.json",
        "complexity_validation_translations.json",
    ):
        pilot = json.loads((processed / filename).read_text(encoding="utf-8"))
        excluded_ids.update(row["document_id"] for row in pilot["records"])
    corpus = json.loads((processed / "motion_corpus.json").read_text(encoding="utf-8"))
    if corpus["completed_through"] != 2025:
        raise ValueError("Complete the 2000-2025 coverage audit before sampling.")

    # Sample by year with a fixed seed and no sentiment or complexity filters
    rng = random.Random(45)
    selected = []
    for year in range(2000, 2026):
        eligible = sorted(
            (
                row
                for row in corpus["records"]
                if row["year"] == year
                and row["input_fr"]
                and row["document_id"] not in excluded_ids
                and not row["exclusion_de"]
                and not row["exclusion_fr"]
            ),
            key=lambda row: row["document_id"],
        )
        selected.extend(
            sorted(rng.sample(eligible, 10), key=lambda row: row["document_id"])
        )

    # Preserve selection before token checks or additional translations
    output = {
        "selection": "Ten pairs per submission year, 2000-2025; sorted eligible IDs; random.Random(45); exclude flagged administrative notices/placeholders; no score, topic, or length filtering.",
        "excluded_development_ids": sorted(excluded_ids),
        "source_file": "motion_corpus.json",
        "text_scope": "Full motion ReasonText; original submission language unverified.",
        "length_policy": "Check model input limits before translating; do not silently truncate or replace selected documents.",
        "records": selected,
    }
    path = processed / "complexity_expanded_pairs.json"
    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Saved {len(selected)} pairs to {path.name}")


if __name__ == "__main__":
    prepare_sample(Path(__file__).resolve().parents[1])
