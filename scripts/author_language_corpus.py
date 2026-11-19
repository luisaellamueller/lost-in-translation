"""Presumed original language of every motion 2000-2025 (author-language proxy).

Curia Vista does not record the language a motion was written in, and
Person.NativeLanguage is empty. We therefore use the submitting member
(BusinessRole.Role 7 = "Urheber(-in)"):

  1. monolingual canton: DE (ZH LU UR SZ OW NW GL ZG SO BS BL SH AR AI SG AG TG),
     FR (VD NE GE JU), IT (TI);
  2. bilingual canton (BE, FR, VS, GR): the language of the member's biography
     fields (Mandates, AdditionalActivity, AdditionalMandate), decided by
     counting frequent French vs German function words;
  3. motions submitted by a committee or parliamentary group: no author language.

Validation of rule 2: for members from monolingual DE/FR cantons whose
biography language can be decided, we report how often it equals the canton
language.

Steps (run from the repository root):
    python scripts/author_language_corpus.py --fetch   # needs internet; saves raw API answers
    python scripts/author_language_corpus.py           # offline, from data/raw/author_api/

Inputs:   data/raw/author_api/business_roles.json, members.json (raw API answers)
          data/processed/motion_corpus.json
Outputs:  data/processed/motion_author_language.csv   one row per motion 2000-2025
          data/processed/french_authored_motions.csv  French-authored motion IDs
          results/author_language_summary.md          numbers used in the report
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://ws.parlament.ch/odata.svc/"
RAW = Path("data/raw/author_api")
PROC = Path("data/processed")
RESULTS = Path("results")

DE = set("ZH LU UR SZ OW NW GL ZG SO BS BL SH AR AI SG AG TG".split())
FR = set("VD NE GE JU".split())
IT = {"TI"}
FR_WORDS = set(
    "le la les des du de et pour dans au aux une un président membre conseiller "
    "conseillère député depuis".split()
)
DE_WORDS = set(
    "der die das und für im von des mitglied präsident gemeinderat kantonsrat seit "
    "bis verwaltungsrat".split()
)
ROLE_FIELDS = [
    "BusinessNumber",
    "Role",
    "MemberCouncilNumber",
    "CommitteeNumber",
    "ParlGroupNumber",
]
MEMBER_FIELDS = [
    "ID",
    "CantonAbbreviation",
    "Mandates",
    "AdditionalActivity",
    "AdditionalMandate",
]


# fetching
def get(query: str) -> list[dict]:
    import requests  # only needed for --fetch

    for attempt in range(5):
        try:
            r = requests.get(BASE + query, params={"$format": "json"}, timeout=60)
            r.raise_for_status()
            return r.json()["d"]
        except Exception:  # network hiccup: back off and retry
            time.sleep(2**attempt)
    raise RuntimeError(f"failed: {query}")


def fetch() -> None:
    """Download motion IDs, author roles and members; save the raw answers."""
    ids: list[int] = []
    for skip in range(0, 100_000, 1000):
        rows = get(
            "Business?$filter=BusinessType eq 5 and Language eq 'DE' "
            "and SubmissionDate ge datetime'2000-01-01T00:00:00' "
            "and SubmissionDate lt datetime'2026-01-01T00:00:00'"
            f"&$select=ID&$orderby=ID&$top=1000&$skip={skip}"
        )
        ids += [r["ID"] for r in rows]
        if len(rows) < 1000:
            break
    roles = []
    for i in range(0, len(ids), 30):
        cond = " or ".join(f"BusinessNumber eq {v}" for v in ids[i : i + 30])
        for r in get(
            f"BusinessRole?$top=1000&$filter=Language eq 'DE' and Role eq 7 and ({cond})"
        ):
            roles.append({f: r.get(f) for f in ROLE_FIELDS})
    roles.sort(key=lambda r: tuple(r[f] or 0 for f in ROLE_FIELDS if f != "Role"))
    member_ids = sorted(
        {r["MemberCouncilNumber"] for r in roles if r["MemberCouncilNumber"]}
    )
    members = []
    for i in range(0, len(member_ids), 30):
        cond = " or ".join(f"ID eq {v}" for v in member_ids[i : i + 30])
        for m in get(f"MemberCouncil?$top=1000&$filter=Language eq 'DE' and ({cond})"):
            members.append({f: m.get(f) for f in MEMBER_FIELDS})
    members.sort(key=lambda m: m["ID"])
    meta = {
        "source": BASE,
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "business_filter": "BusinessType eq 5 and Language eq 'DE' and 2000-01-01 <= SubmissionDate < 2026-01-01",
        "role_filter": "Language eq 'DE' and Role eq 7 (Urheber/-in)",
    }
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "business_roles.json").write_text(
        json.dumps(
            {"meta": meta, "business_ids": ids, "rows": roles},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    (RAW / "members.json").write_text(
        json.dumps({"meta": meta, "rows": members}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(
        f"Saved {len(ids)} motions, {len(roles)} author roles, {len(members)} members to {RAW}/"
    )


# classification
def bio_language(text: str) -> str | None:
    words = re.findall(r"[a-zäöüéèàç]+", (text or "").lower())
    f = sum(w in FR_WORDS for w in words)
    d = sum(w in DE_WORDS for w in words)
    return "FR" if f > d else "DE" if d > f else None


def biography(member: dict) -> str:
    return " ".join(
        filter(
            None,
            [
                member.get("Mandates"),
                member.get("AdditionalActivity"),
                member.get("AdditionalMandate"),
            ],
        )
    )


def member_language(member: dict) -> tuple[str, str]:
    canton = member.get("CantonAbbreviation") or ""
    if canton in DE:
        return "DE", "canton"
    if canton in FR:
        return "FR", "canton"
    if canton in IT:
        return "IT", "canton"
    lang = bio_language(biography(member))
    return (lang, "bilingual canton + biography language") if lang else ("", "unknown")


def classify() -> None:
    roles = json.loads((RAW / "business_roles.json").read_text(encoding="utf-8"))
    members = {
        m["ID"]: m
        for m in json.loads((RAW / "members.json").read_text(encoding="utf-8"))["rows"]
    }
    by_business: dict[int, list[dict]] = {}
    for r in roles["rows"]:
        by_business.setdefault(r["BusinessNumber"], []).append(r)

    rows = []
    for bid in roles["business_ids"]:
        authors = by_business.get(bid, [])
        member_rows = [r for r in authors if r["MemberCouncilNumber"] in members]
        if member_rows:
            m = members[member_rows[0]["MemberCouncilNumber"]]
            lang, method = member_language(m)
            rows.append(
                {
                    "document_id": bid,
                    "author_type": "member",
                    "member_id": m["ID"],
                    "canton": m.get("CantonAbbreviation") or "",
                    "author_language": lang,
                    "method": method,
                }
            )
        else:
            kind = (
                "committee"
                if any(r["CommitteeNumber"] for r in authors)
                else (
                    "parl_group"
                    if any(r["ParlGroupNumber"] for r in authors)
                    else "none"
                )
            )
            rows.append(
                {
                    "document_id": bid,
                    "author_type": kind,
                    "member_id": "",
                    "canton": "",
                    "author_language": "",
                    "method": kind,
                }
            )

    with open(
        PROC / "motion_author_language.csv", "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    french = [r for r in rows if r["author_language"] == "FR"]
    with open(
        PROC / "french_authored_motions.csv", "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["document_id", "method"])
        w.writerows([r["document_id"], r["method"]] for r in french)

    # Validation of the biography rule on members from monolingual DE/FR cantons
    checked = agree = 0
    for m in members.values():
        canton = m.get("CantonAbbreviation")
        if canton in DE or canton in FR:
            lang = bio_language(biography(m))
            if lang:
                checked += 1
                agree += lang == ("DE" if canton in DE else "FR")

    corpus = json.loads((PROC / "motion_corpus.json").read_text(encoding="utf-8"))[
        "records"
    ]
    eligible = [
        r
        for r in corpus
        if r["exclusion_de"] is None
        and r["exclusion_fr"] is None
        and r["reference_de"]
        and r["input_fr"]
    ]
    lang_of = {r["document_id"]: r["author_language"] or r["author_type"] for r in rows}
    in_pairs = Counter(
        lang_of.get(int(r["document_id"]), "not found") for r in eligible
    )
    multi = sum(
        len([r for r in v if r["MemberCouncilNumber"]]) > 1
        for v in by_business.values()
    )

    RESULTS.mkdir(exist_ok=True)
    lines = [
        "# Author language of motions 2000-2025",
        "",
        f"Raw API answers retrieved {roles['meta']['retrieved']} ({RAW}/).",
        "",
        f"- Motions 2000-2025 in the API: {len(rows):,}",
        f"- Members who submitted at least one motion: {len(members):,}",
        f"- Motions with more than one member as author (first one used): {multi}",
        f"- Biography rule check (members from monolingual DE/FR cantons with a decidable "
        f"biography language): {agree} of {checked} agree with the canton language",
        "",
        "| Author language | All motions | Eligible DE-FR pairs |",
        "|---|---:|---:|",
    ]
    all_counts = Counter(r["author_language"] or r["author_type"] for r in rows)
    for key in sorted(
        set(all_counts) | set(in_pairs), key=lambda k: -all_counts.get(k, 0)
    ):
        lines.append(
            f"| {key} | {all_counts.get(key, 0):,} | {in_pairs.get(key, 0):,} |"
        )
    lines += [
        "",
        f"Eligible pairs: {len(eligible):,}; French-authored eligible pairs: {in_pairs.get('FR', 0):,}.",
    ]
    (RESULTS / "author_language_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--fetch",
        action="store_true",
        help="download the raw API answers first (needs internet)",
    )
    args = ap.parse_args()
    if args.fetch:
        fetch()
    classify()


if __name__ == "__main__":
    main()
