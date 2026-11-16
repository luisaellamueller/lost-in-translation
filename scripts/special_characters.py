"""RQ3 surface conventions: ß and dashes in machine and official German.

1. Storage check (footnote): before 2023 the API returns plain substitutes for
   special characters. We count French justifications containing "oeuvre" vs
   "œuvre" and texts containing guillemets, before and from 2023.
2. Table 2 (2023-2025 only): texts containing ß or a spaced en dash (" – ") in
     - our machine output (French-authored sample, all years),
     - official German translations of French-authored motions,
     - official German texts of motions by German- or Italian-speaking members.
3. The official texts with ß: who submitted them, and a one-sided Fisher exact
   test of "no French-authored text contains ß".
4. Dashes per year 2023-2025 in both groups of official texts.

Requires data/processed/motion_author_language.csv (scripts/author_language_corpus.py).

Run from the repository root:
    python scripts/special_characters.py
Output: results/special_characters.md
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from math import comb
from pathlib import Path

PROC = Path("data/processed")
DASH = " – "  # spaced en dash, the German Gedankenstrich (not ranges such as 2023–2025)


def fisher_zero_one_sided(n_group: int, n_other: int, hits_total: int) -> float:
    """P(no hit in a group of n_group) if hits_total hits fall at random among all texts."""
    return comb(n_other, hits_total) / comb(n_group + n_other, hits_total)


def main() -> None:
    corpus = json.loads((PROC / "motion_corpus.json").read_text(encoding="utf-8"))["records"]
    with open(PROC / "motion_author_language.csv", encoding="utf-8") as f:
        author = {int(r["document_id"]): r for r in csv.DictReader(f)}
    mt = json.loads((PROC / "complexity_fr_author_translations.json").read_text(encoding="utf-8"))["records"]

    lines = ["# ß and dashes in machine and official German", ""]

    # 1. storage check
    lines += ["## Storage of special characters in the API", "",
              "| Period | French texts | with 'oeuvre' | with 'œuvre' | with « » |", "|---|---:|---:|---:|---:|"]
    for label, cond in (("2000-2022", lambda y: y < 2023), ("2023-2025", lambda y: y >= 2023)):
        texts = [r["input_fr"] for r in corpus if r["input_fr"] and cond(int(r["year"]))]
        lines.append(f"| {label} | {len(texts):,} | {sum('oeuvre' in t for t in texts):,} | "
                     f"{sum('œuvre' in t for t in texts):,} | {sum('«' in t for t in texts):,} |")

    # 2. table for 2023-2025
    eligible = [r for r in corpus if r["exclusion_de"] is None and r["reference_de"] and int(r["year"]) >= 2023]
    lang = lambda r: author.get(int(r["document_id"]), {}).get("author_language", "")
    groups = {
        "Official German translations of French-authored motions": [r for r in eligible if lang(r) == "FR"],
        "Official German texts by German- or Italian-speaking members": [r for r in eligible if lang(r) in ("DE", "IT")],
    }
    has_ss = lambda t: "ß" in t
    has_dash = lambda t: DASH in t
    lines += ["", "## Table 2 (official texts: 2023-2025)", "",
              "| Texts | n | with ß | with dash |", "|---|---:|---:|---:|",
              f"| Our MT model (French-authored sample, all years) | {len(mt)} | "
              f"{sum(has_ss(r['translation_de']) for r in mt)} | {sum(has_dash(r['translation_de']) for r in mt)} |"]
    for name, rows in groups.items():
        lines.append(f"| {name} | {len(rows):,} | {sum(has_ss(r['reference_de']) for r in rows)} | "
                     f"{sum(has_dash(r['reference_de']) for r in rows)} |")
    lines.append(f"\nOfficial translations in the 259-pair sample with a dash: "
                 f"{sum(has_dash(r['reference_de']) for r in mt)} (machine: {sum(has_dash(r['translation_de']) for r in mt)}).")

    # 3. who wrote the official texts with ß
    ss_rows = [r for r in eligible if has_ss(r["reference_de"])]
    by_lang = Counter(lang(r) or author.get(int(r["document_id"]), {}).get("author_type", "unknown") for r in ss_rows)
    members = {author[int(r["document_id"])]["member_id"] for r in ss_rows if int(r["document_id"]) in author}
    words = Counter(w for r in ss_rows for w in re.findall(r"\w*ß\w*", r["reference_de"]))
    n_fr = len(groups["Official German translations of French-authored motions"])
    n_other = len(groups["Official German texts by German- or Italian-speaking members"])
    k = sum(has_ss(r["reference_de"]) for r in groups["Official German texts by German- or Italian-speaking members"])
    lines += ["", "## Official 2023-2025 texts containing ß", "",
              f"- Texts: {len(ss_rows)}; by author language: {dict(by_lang)}; distinct submitting members: {len(members)}",
              f"- Most frequent ß words: {', '.join(f'{w} ({n})' for w, n in words.most_common(8))}",
              f"- One-sided Fisher exact test, P(no ß among {n_fr} French-authored texts | {k} ß texts "
              f"among {n_fr + n_other}): p = {fisher_zero_one_sided(n_fr, n_other, k):.4f}", ""]
    for r in ss_rows:
        a = author.get(int(r["document_id"]), {})
        lines.append(f"  - {r['document_id']} ({r['year']}): member {a.get('member_id', '?')}, "
                     f"canton {a.get('canton', '?')}, language {a.get('author_language', '?')}")

    # 4. dashes per year
    lines += ["", "## Share of official texts with a dash, per year", "",
              "| Year | French-authored (translated) | German/Italian-authored |", "|---|---:|---:|"]
    for y in (2023, 2024, 2025):
        cells = []
        for rows in groups.values():
            ry = [r for r in rows if int(r["year"]) == y]
            cells.append(f"{sum(has_dash(r['reference_de']) for r in ry)}/{len(ry)} "
                         f"({100 * sum(has_dash(r['reference_de']) for r in ry) / len(ry):.0f}%)")
        lines.append(f"| {y} | {cells[0]} | {cells[1]} |")

    Path("results").mkdir(exist_ok=True)
    Path("results/special_characters.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
