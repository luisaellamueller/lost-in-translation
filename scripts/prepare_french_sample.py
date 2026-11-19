"""Fixed sample of French-authored motions for the clean comparison.

Why: in the original 260-motion sample only 63 motions were submitted by
French-speaking members. For most others the official German is the original
and the model translated a translation back (German -> French -> German).
This sample keeps only motions whose submitter is French-speaking, so the
official German is (presumably) a human translation of the French input.

Author language (data/processed/french_authored_motions.csv, retrieved from
Curia Vista on 15 Nov 2026 with the same rule as scripts/author_language.py):
monolingual French-speaking canton (VD, NE, GE, JU), or a bilingual canton
(BE, FR, VS, GR) with a French-language biography text.

Sampling rule (fixed before any new translation or scoring):
  * eligible German-French pairs from motion_corpus.json, French-authored,
    excluding the 30 development documents;
  * 10 per submission year 2000-2025;
  * French-authored documents that are already in the original translation
    sample (a uniform random draw within year) are kept, and each year is
    topped up uniformly at random from the remaining French-authored
    documents with random.Random(48). The result is a uniform random sample
    within year, and the 63 existing translations are reused unchanged.

Outputs in data/processed/:
  complexity_fr_author_pairs.json          the fixed sample (translation input)
  complexity_fr_author_translations.json   seeded with the reused translations;
                                           translate_pilot() resumes from it

Run from the repository root:
    python scripts/prepare_french_sample.py           # draw the sample (refuses to overwrite)
    python scripts/prepare_french_sample.py --check   # redraw in memory and compare with the saved sample
"""

from __future__ import annotations

import csv
import json
import argparse
import random
from pathlib import Path

PROC = Path("data/processed")
PER_YEAR = 10
SEED = 48
PAIRS_OUT = PROC / "complexity_fr_author_pairs.json"
TRANSLATIONS_OUT = PROC / "complexity_fr_author_translations.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--check",
        action="store_true",
        help="redraw the sample in memory and compare it with the saved one",
    )
    check = ap.parse_args().check
    if not check and (PAIRS_OUT.exists() or TRANSLATIONS_OUT.exists()):
        raise SystemExit(
            "Sample files already exist — not overwriting a fixed sample. "
            "Delete them deliberately if you really want to redraw."
        )

    corpus = json.loads((PROC / "motion_corpus.json").read_text(encoding="utf-8"))[
        "records"
    ]
    with open(PROC / "french_authored_motions.csv", encoding="utf-8") as f:
        french = {int(r["document_id"]) for r in csv.DictReader(f)}
    old_pairs = json.loads(
        (PROC / "complexity_expanded_pairs.json").read_text(encoding="utf-8")
    )
    development = {int(i) for i in old_pairs["excluded_development_ids"]}
    old_tr = json.loads(
        (PROC / "complexity_expanded_translations.json").read_text(encoding="utf-8")
    )
    reusable = {
        int(r["document_id"]): r for r in old_tr["records"]
    }  # completed outputs only

    eligible = [
        r
        for r in corpus
        if r["exclusion_de"] is None
        and r["exclusion_fr"] is None
        and r["reference_de"]
        and r["input_fr"]
        and int(r["document_id"]) in french
        and int(r["document_id"]) not in development
    ]

    rng = random.Random(SEED)
    selected, reused = [], []
    for year in range(2000, 2026):
        pool = sorted(
            (r for r in eligible if int(r["year"]) == year),
            key=lambda r: int(r["document_id"]),
        )
        keep = [r for r in pool if int(r["document_id"]) in reusable]
        rest = [r for r in pool if int(r["document_id"]) not in reusable]
        if len(keep) + len(rest) < PER_YEAR:
            raise SystemExit(
                f"Only {len(pool)} eligible French-authored motions in {year}."
            )
        chosen = keep[:PER_YEAR] + rng.sample(rest, PER_YEAR - len(keep[:PER_YEAR]))
        selected += sorted(chosen, key=lambda r: int(r["document_id"]))
        reused += [int(r["document_id"]) for r in keep[:PER_YEAR]]

    if check:
        saved = [
            int(r["document_id"])
            for r in json.loads(PAIRS_OUT.read_text(encoding="utf-8"))["records"]
        ]
        redrawn = [int(r["document_id"]) for r in selected]
        print(
            f"Eligible French-authored pairs (development IDs excluded): {len(eligible)}"
        )
        print(
            f"Redrawn sample identical to {PAIRS_OUT}: {saved == redrawn} ({len(redrawn)} IDs)"
        )
        if saved != redrawn:
            raise SystemExit(1)
        return

    PAIRS_OUT.write_text(
        json.dumps(
            {
                "selection": (
                    f"{PER_YEAR} French-authored eligible pairs per submission year 2000-2025; "
                    f"French-authored documents from the original sample kept, rest drawn with "
                    f"random.Random({SEED}) from sorted IDs; development IDs excluded."
                ),
                "author_language_source": "french_authored_motions.csv (Curia Vista, retrieved 2026-11-15)",
                "excluded_development_ids": sorted(development),
                "reused_translation_ids": sorted(reused),
                "source_file": "motion_corpus.json",
                "text_scope": "Full motion ReasonText; original language inferred from the submitting member.",
                "records": selected,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Seed the new translation file with the reused outputs (same model and settings)
    seeded = {
        k: old_tr[k]
        for k in ("model_file", "settings", "source_language", "target_language")
    }
    seeded["records"] = [reusable[i] for i in sorted(reused)]
    seeded["failed_records"] = []
    TRANSLATIONS_OUT.write_text(
        json.dumps(seeded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Eligible French-authored pairs: {len(eligible)}")
    print(
        f"Selected: {len(selected)} ({PER_YEAR} per year); reused translations: {len(reused)}; "
        f"to translate: {len(selected) - len(reused)}"
    )
    print(f"Wrote {PAIRS_OUT} and {TRANSLATIONS_OUT}")


if __name__ == "__main__":
    main()
