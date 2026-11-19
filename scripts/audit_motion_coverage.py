import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from prepare_pilot import clean_text


def download_year(year: int, language: str, raw_dir: Path) -> list[dict[str, Any]]:
    """Download a complete year of motions, preserving each response page.

    Args:
        year: Submission year.
        language: DE or FR.
        raw_dir: Directory for response pages and retrieval metadata.

    Returns:
        All motion records for the requested year and language.
    """
    # Retrieve fixed-size pages and reuse completed downloads
    records = []
    offset = 0
    while True:
        params = {
            "$filter": f"BusinessType eq 5 and Language eq '{language}' and SubmissionDate ge datetime'{year}-01-01T00:00:00' and SubmissionDate lt datetime'{year + 1}-01-01T00:00:00'",
            "$select": "ID,Language,BusinessType,Title,ReasonText,SubmissionDate",
            "$orderby": "ID",
            "$format": "json",
            "$top": 500,
            "$skip": offset,
        }
        url = "https://ws.parlament.ch/OData.svc/Business?" + urlencode(params)
        path = raw_dir / f"motions_{year}_{language.lower()}_offset_{offset}.json"
        metadata_path = path.with_suffix(".metadata.json")
        if not path.exists():
            with urlopen(url, timeout=60) as response:
                content = response.read()
            json.loads(content)
            path.write_bytes(content)
            metadata_path.write_text(
                json.dumps(
                    {
                        "query_url": url,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        page = json.loads(path.read_text(encoding="utf-8"))["d"]
        rows = page if isinstance(page, list) else page["results"]
        records.extend(rows)
        if len(rows) < 500:
            break
        offset += len(rows)

    # Allow exact server duplicates but reject conflicting versions of an ID
    seen = {}
    for row in records:
        if row["ID"] in seen and row != seen[row["ID"]]:
            raise ValueError(
                f"Conflicting records for {row['ID']} in {year} {language}."
            )
        seen[row["ID"]] = row
    return records


def audit_coverage(project_dir: Path) -> None:
    """Save yearly coverage and cleaned German/French motion justifications.

    Args:
        project_dir: Project directory containing data/raw and data/processed.
    """
    # Preserve all usable German texts, including those without a French match
    coverage = []
    corpus = []
    # Flag verified notices without removing genuine short arguments
    oral_notices = {
        "mündlich",
        "erfolgt mündlich",
        "oral",
        "par oral",
        "suivra par oral",
        "fera l'objet d'un compte rendu oral",
    }
    reference_only_ids = {
        20003407,
        20003408,
        20023150,
        20023381,
        20023469,
        20023470,
        20053001,
        20053468,
        20053469,
        20063176,
        20063177,
        20073277,
        20103391,
        20103392,
        20103393,
        20103394,
        20103395,
        20103630,
        20103631,
        20103632,
        20103633,
        20103634,
        20123648,
        20144009,
        20144010,
        20173013,
        20194382,
    }
    for year in range(2000, 2026):
        languages = {}
        totals = {}
        duplicates = {}
        for language in ("DE", "FR"):
            rows = download_year(year, language, project_dir / "data/raw")
            totals[language] = len(rows)
            duplicates[language] = len(rows) - len({row["ID"] for row in rows})
            texts = {}
            for row in rows:
                markup = (row["ReasonText"] or "").strip()
                text = clean_text(markup) if markup else ""
                if text:
                    texts[row["ID"]] = {**row, "text": text}
            languages[language] = texts
        german, french = languages["DE"], languages["FR"]
        paired_ids = german.keys() & french.keys()
        coverage.append(
            {
                "year": year,
                "de_records": totals["DE"],
                "fr_records": totals["FR"],
                "de_exact_duplicate_rows": duplicates["DE"],
                "fr_exact_duplicate_rows": duplicates["FR"],
                "de_with_justification": len(german),
                "fr_with_justification": len(french),
                "paired_justifications": len(paired_ids),
            }
        )
        for document_id, de in sorted(german.items()):
            fr = french.get(document_id)
            date = datetime.fromtimestamp(
                int(de["SubmissionDate"][6:-2]) / 1000, timezone.utc
            ).date()
            if date.year != year:
                raise ValueError(f"Submission year mismatch for {document_id}.")
            exclusions = {}
            for language, row in (("de", de), ("fr", fr)):
                reason = None
                if row:
                    text = row["text"]
                    if (
                        not any(char.isalpha() for char in text)
                        or text.casefold() == "xxx"
                    ):
                        reason = "placeholder"
                    elif text.casefold().rstrip(".! ") in oral_notices:
                        reason = "oral justification notice"
                    elif language == "de" and document_id in reference_only_ids:
                        reason = (
                            "reference to external document only; manually verified"
                        )
                exclusions[language] = reason
            corpus.append(
                {
                    "document_id": document_id,
                    "year": year,
                    "submission_date": date.isoformat(),
                    "title_de": de["Title"],
                    "reference_de": de["text"],
                    "title_fr": fr["Title"] if fr else None,
                    "input_fr": fr["text"] if fr else None,
                    "record_url_de": de["__metadata"]["uri"],
                    "record_url_fr": fr["__metadata"]["uri"] if fr else None,
                    "exclusion_de": exclusions["de"],
                    "exclusion_fr": exclusions["fr"],
                }
            )

        year_records = [row for row in corpus if row["year"] == year]
        coverage[-1]["de_substantive_justifications"] = sum(
            not row["exclusion_de"] for row in year_records
        )
        coverage[-1]["substantive_pairs"] = sum(
            bool(row["input_fr"])
            and not row["exclusion_de"]
            and not row["exclusion_fr"]
            for row in year_records
        )

        # Checkpoint the audit after each complete year
        output = project_dir / "data/processed"
        (output / "motion_coverage.json").write_text(
            json.dumps(
                {
                    "scope": "BusinessType 5; full ReasonText; submission years 2000-2025.",
                    "completed_through": year,
                    "years": coverage,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (output / "motion_corpus.json").write_text(
            json.dumps(
                {
                    "scope": "Official German motion justifications, with French counterparts where available; original language unverified.",
                    "completed_through": year,
                    "records": corpus,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(coverage[-1], flush=True)


if __name__ == "__main__":
    # Audit complete calendar years before selecting translations
    audit_coverage(Path(__file__).resolve().parents[1])
