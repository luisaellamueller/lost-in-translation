import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lxml import html


def clean_text(markup: str) -> str:
    """Remove HTML while keeping paragraphs and list items separate.

    Args:
        markup: Submitted text from a Curia Vista record.

    Returns:
        Plain text with one nonempty paragraph or list item per line.
    """
    # Preserve boundaries before removing tags
    markup = re.sub(r"</(?:p|li)>|<br\s*/?>", "\n", markup, flags=re.IGNORECASE)
    text = html.fromstring(markup).text_content()
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def prepare_pilot(project_dir: Path) -> list[dict[str, Any]]:
    """Sample five paired interpellations from the historical snapshots.

    Args:
        project_dir: Directory containing the German and French 2000 snapshots.

    Returns:
        Five records containing full submitted texts, titles, and provenance.
    """
    german = json.loads(
        (project_dir / "data/raw/interpellations_2000_de.json").read_text(
            encoding="utf-8"
        )
    )["d"]
    french = json.loads(
        (project_dir / "data/raw/interpellations_2000_fr.json").read_text(
            encoding="utf-8"
        )
    )["d"]
    german_by_id = {row["ID"]: row for row in german}
    french_by_id = {row["ID"]: row for row in french}

    # Select matching interpellations with submitted text
    matching_ids = sorted(german_by_id.keys() & french_by_id.keys())
    eligible_ids = [
        document_id
        for document_id in matching_ids
        if german_by_id[document_id]["BusinessType"] == 8
        and french_by_id[document_id]["BusinessType"] == 8
        and (german_by_id[document_id]["SubmittedText"] or "").strip()
        and (french_by_id[document_id]["SubmittedText"] or "").strip()
    ]

    # Pair complete texts by document ID, not paragraph position
    pairs = []
    for document_id in sorted(random.Random(42).sample(eligible_ids, 5)):
        de = german_by_id[document_id]
        fr = french_by_id[document_id]
        # Convert API milliseconds to a calendar date in UTC
        timestamp = int(de["SubmissionDate"][6:-2]) / 1000
        submission_date = (
            datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
        )
        pairs.append(
            {
                "document_id": document_id,
                "submission_date": submission_date,
                "title_de": de["Title"].strip(),
                "title_fr": fr["Title"].strip(),
                "input_fr": clean_text(fr["SubmittedText"]),
                "reference_de": clean_text(de["SubmittedText"]),
                "record_url_fr": fr["__metadata"]["uri"],
                "record_url_de": de["__metadata"]["uri"],
            }
        )
    return pairs


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parents[1]
    pairs = prepare_pilot(project_dir)
    output = {
        "purpose": "Development pilot; not the final evaluation sample.",
        "selection": "Five shared IDs sampled without replacement from sorted eligible IDs using random.Random(42); ordinary interpellations submitted in 2000 with nonempty DE and FR SubmittedText.",
        "source_files": [
            "data/raw/interpellations_2000_de.json",
            "data/raw/interpellations_2000_fr.json",
        ],
        "provenance": "Curia Vista OData snapshots; exact queries and UTC retrieval times are saved in the source files.",
        "text_scope": "Full SubmittedText only; excludes ReasonText and government responses.",
        "source_language": "Unverified. French is the designated input; German is the official reference.",
        "records": pairs,
    }
    output_path = project_dir / "data/processed/pilot_pairs.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Saved {len(pairs)} pairs to {output_path.name}")
