"""Presumed original language of the 260 sampled motions, and results by group.

Curia Vista does not record the language a motion was written in. The usual
proxy is the submitting member's language. Person.NativeLanguage turned out to
be empty for all sampled members (checked 15 Nov 2026), so we use:
  1. the member's canton, if it is monolingual (DE / FR / IT), otherwise
  2. for bilingual cantons (BE, FR, VS, GR): the language of the member's
     biography fields (Mandates, AdditionalActivity), which agreed with the
     canton language in 140 of 140 members from monolingual cantons;
  3. committees and parliamentary groups: no single author language.

Run from the repository root (needs internet access to ws.parlament.ch):
    python scripts/author_language.py           # query API, write CSV, print comparison
    python scripts/author_language.py --offline # reuse the saved CSV
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import random
import re
import statistics as st
import time
from pathlib import Path

import requests

BASE = "https://ws.parlament.ch/odata.svc/"
PAIRS = Path("data/processed/complexity_expanded_pairs.json")
RESULTS = Path("data/processed/complexity_expanded_results.json")
OUT = Path("data/processed/sample_author_language.csv")

DE = set("ZH LU UR SZ OW NW GL ZG SO BS BL SH AR AI SG AG TG".split())
FR = set("VD NE GE JU".split())
IT = {"TI"}
FR_WORDS = set("le la les des du de et pour dans au aux une un président membre conseiller conseillère député depuis".split())
DE_WORDS = set("der die das und für im von des mitglied präsident gemeinderat kantonsrat seit bis verwaltungsrat".split())


def get(query: str) -> list[dict]:
    for attempt in range(4):
        try:
            r = requests.get(BASE + query, params={"$format": "json"}, timeout=60)
            r.raise_for_status()
            return [{k: v for k, v in row.items() if not isinstance(v, dict)} for row in r.json()["d"]]
        except (requests.RequestException, ValueError):
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed: {query}")


def batched(entity: str, field: str, values: list, extra: str) -> list[dict]:
    rows = []
    for i in range(0, len(values), 30):
        cond = " or ".join(f"{field} eq {v}" for v in values[i:i + 30])
        rows += get(f"{entity}?$top=1000&$filter=Language eq 'DE' and {extra}({cond})")
    return rows


def bio_language(text: str) -> str | None:
    words = re.findall(r"[a-zäöüéèàç]+", (text or "").lower())
    f, d = sum(w in FR_WORDS for w in words), sum(w in DE_WORDS for w in words)
    return "FR" if f > d else "DE" if d > f else None


def query_api() -> list[dict]:
    ids = [int(r["document_id"]) for r in json.loads(PAIRS.read_text(encoding="utf-8"))["records"]]
    roles = batched("BusinessRole", "BusinessNumber", ids, "Role eq 7 and ")  # 7 = Urheber(-in)
    mem_ids = sorted({r["MemberCouncilNumber"] for r in roles if r.get("MemberCouncilNumber")})
    members = {m["ID"]: m for m in batched("MemberCouncil", "ID", mem_ids, "")}
    out = []
    for r in roles:
        m = members.get(r.get("MemberCouncilNumber"))
        author = "member" if m else "committee" if r.get("CommitteeNumber") else \
                 "parl_group" if r.get("ParlGroupNumber") else "other"
        canton = m.get("CantonAbbreviation") if m else ""
        lang, method = "", author
        if m:
            if canton in DE | FR | IT:
                lang, method = ("DE" if canton in DE else "FR" if canton in FR else "IT"), "canton"
            else:
                bio = " ".join(filter(None, [m.get("Mandates"), m.get("AdditionalActivity"), m.get("AdditionalMandate")]))
                lang = bio_language(bio) or ""
                method = "bilingual canton + biography language" if lang else "unknown"
        out.append({"document_id": r["BusinessNumber"], "author_type": author, "canton": canton or "",
                    "author_language": lang, "method": method})
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    return out


def compare(rows: list[dict]) -> None:
    lang = {int(r["document_id"]): r["author_language"] or r["author_type"] for r in rows}
    res = json.loads(RESULTS.read_text(encoding="utf-8"))["records"]
    parse = lambda v: v if isinstance(v, dict) else ast.literal_eval(v)
    measures = [("Words per sentence", "mean_sentence_words"), ("Max. tree depth", "mean_sentence_tree_depth"),
                ("Content-word Zipf", "mean_content_word_zipf"), ("MATTR (50)", "mattr_50"),
                ("Subordinators / 100", "subordinators_per_100_words"),
                ("Relative markers / 100", "relative_markers_per_100_words"), ("LIX", "lix")]
    for group in ["FR", "DE", "IT"]:
        rr = [r for r in res if lang.get(int(r["document_id"])) == group]
        print(f"\n== author language {group}: {len(rr)} pairs  (machine minus official, 95% bootstrap CI)")
        for label, k in measures:
            d = [parse(r["generated"])[k] - parse(r["official"])[k] for r in rr
                 if parse(r["generated"]).get(k) is not None and parse(r["official"]).get(k) is not None]
            rng = random.Random(47)
            boots = sorted(st.mean(rng.choices(d, k=len(d))) for _ in range(2000))
            print(f"   {label:24s} {st.mean(d):+.3f}  [{boots[49]:+.3f}, {boots[1950]:+.3f}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="reuse the saved CSV instead of querying the API")
    args = ap.parse_args()
    if args.offline:
        with open(OUT, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        rows = query_api()
    counts: dict[str, int] = {}
    for r in rows:
        key = r["author_language"] or r["author_type"]
        counts[key] = counts.get(key, 0) + 1
    print("Presumed original language of the sample:", counts)
    compare(rows)


if __name__ == "__main__":
    main()
