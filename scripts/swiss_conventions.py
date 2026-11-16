"""Swiss conventions and parliamentary terminology: official vs machine German.

Two outputs, both computed on the same 259 completed translation pairs:

1. results/swiss_conventions_counts.md
   Automatic counts of Swiss vs German-German conventions (unambiguous
   surface features: ß, quotation marks, thousands separators).

2. results/terminology_review.csv  (open in Excel / Numbers / Google Sheets)
   One row per occurrence of a Swiss parliamentary term in the French source,
   with the French sentence and the closest sentences of both German versions.
   Fill in the empty columns by hand:
     official_ok / machine_ok : yes | no | unclear
     machine_rendering        : how the model translated the term
     note                     : anything worth reporting
   Then run with --summarise to turn your annotations into a table.

Run from the repository root:
    python scripts/swiss_conventions.py               # create counts + review sheet
    python scripts/swiss_conventions.py --summarise   # after annotating the CSV
    python scripts/swiss_conventions.py --french      # same, for the French-authored sample
    python scripts/swiss_conventions.py --french --summarise
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

TRANSLATIONS = Path("data/processed/complexity_expanded_translations.json")
OUT = Path("results")

# French term (regex, lower case) -> expected Swiss German term(s) (regex)
TERMS: dict[str, tuple[str, str]] = {
    "motion": (r"\bmotions?\b", r"\bmotion(en)?\b"),
    "postulat": (r"\bpostulats?\b", r"\bpostulat(e|s)?\b"),
    "interpellation": (r"\binterpellations?\b", r"\binterpellation(en)?\b"),
    "initiative parlementaire": (r"\binitiatives? parlementaires?\b", r"\bparlamentarische[nr]? initiative(n)?\b"),
    "Conseil fédéral": (r"\bconseil fédéral\b", r"\bbundesrat(e?s)?\b"),
    "Conseil national": (r"\bconseil national\b", r"\bnationalrat(e?s)?\b"),
    "Conseil des Etats": (r"\bconseil des [ée]tats\b", r"\bständerat(e?s)?\b"),
}
# common wrong or generic renderings, used only to pre-fill a suggestion
GENERIC = r"\b(antrag|anträge|anfrage|vorschlag|vorstoss|vorstoß|bundesregierung|bundesrats?rat|staatsrat)\w*"

CONVENTIONS = {
    "ß (never used in Swiss German)": r"ß",
    "German quotes „ “": r"[„“]",
    "Swiss quotes « »": r"[«»]",
    "thousands with dot (10.000)": r"\b\d{1,3}\.\d{3}\b",
    "thousands with space/apostrophe (10 000, 10'000)": r"\b\d{1,3}[  '’]\d{3}\b",
}

SENT = re.compile(r"(?<=[.!?:;])\s+|\n+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT.split(text) if s.strip()]


def window(sents: list[str], rel: float, width: int = 1) -> str:
    """Sentences around the same relative position as the French sentence."""
    if not sents:
        return ""
    i = min(int(rel * len(sents)), len(sents) - 1)
    return " ".join(sents[max(0, i - width): i + width + 1])


def load() -> list[dict]:
    return json.loads(TRANSLATIONS.read_text(encoding="utf-8"))["records"]


def convention_counts(recs: list[dict]) -> str:
    rows = ["| Feature | Official German | Machine German |", "|---|---:|---:|"]
    for name, pat in CONVENTIONS.items():
        o = sum(bool(re.search(pat, r["reference_de"])) for r in recs)
        m = sum(bool(re.search(pat, r["translation_de"])) for r in recs)
        rows.append(f"| {name} | {o} | {m} |")
    head = (f"# Swiss conventions in the {len(recs)} completed pairs\n\n"
            "Number of texts containing the feature at least once.\n\n")
    return head + "\n".join(rows) + "\n"


def review_rows(recs: list[dict]) -> list[dict]:
    rows = []
    for r in recs:
        fr_sents = sentences(r["input_fr"])
        off_sents, mt_sents = sentences(r["reference_de"]), sentences(r["translation_de"])
        for term, (fr_pat, de_pat) in TERMS.items():
            for k, s in enumerate(fr_sents):
                if not re.search(fr_pat, s, re.I):
                    continue
                rel = k / max(len(fr_sents), 1)
                off_ctx, mt_ctx = window(off_sents, rel), window(mt_sents, rel)
                generic = re.findall(GENERIC, mt_ctx, re.I)
                rows.append({
                    "document_id": r["document_id"], "year": r["year"], "term": term,
                    "french_sentence": s,
                    "official_context": off_ctx, "machine_context": mt_ctx,
                    "auto_official_has_term": "yes" if re.search(de_pat, r["reference_de"], re.I) else "no",
                    "auto_machine_has_term": "yes" if re.search(de_pat, r["translation_de"], re.I) else "no",
                    "auto_machine_generic_word": ", ".join(sorted(set(g.lower() for g in generic))),
                    "official_ok": "", "machine_ok": "", "machine_rendering": "", "note": "",
                })
    return rows


def summarise(path: Path) -> None:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    done = [r for r in rows if r["machine_ok"].strip()]
    print(f"{len(done)} of {len(rows)} rows annotated\n")
    print("| Term | Cases | Official correct | Machine correct | Machine unclear |")
    print("|---|---:|---:|---:|---:|")
    for term in TERMS:
        g = [r for r in done if r["term"] == term]
        if not g:
            continue
        ok = lambda col, v: sum(r[col].strip().lower() == v for r in g)
        print(f"| {term} | {len(g)} | {ok('official_ok', 'yes')} | {ok('machine_ok', 'yes')} | {ok('machine_ok', 'unclear')} |")
    wrong = [r for r in done if r["machine_ok"].strip().lower() == "no"]
    if wrong:
        print("\nMachine renderings marked wrong:")
        for r in wrong:
            print(f"  {r['document_id']} {r['term']}: {r['machine_rendering']}  {r['note']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summarise", action="store_true", help="summarise the annotated review sheet")
    ap.add_argument("--french", action="store_true", help="use the French-authored sample")
    args = ap.parse_args()
    global TRANSLATIONS
    suffix = "_french" if args.french else ""
    if args.french:
        TRANSLATIONS = Path("data/processed/complexity_fr_author_translations.json")
    OUT.mkdir(exist_ok=True)
    sheet = OUT / f"terminology_review{suffix}.csv"
    if args.summarise:
        summarise(sheet)
        return
    recs = load()
    (OUT / f"swiss_conventions_counts{suffix}.md").write_text(convention_counts(recs), encoding="utf-8")
    rows = review_rows(recs)
    if sheet.exists():
        raise SystemExit(f"{sheet} already exists — not overwriting your annotations. "
                         "Delete or rename it to create a fresh sheet.")
    with open(sheet, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel shows umlauts
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(convention_counts(recs))
    print(f"Review sheet: {sheet} ({len(rows)} term occurrences in "
          f"{len({r['document_id'] for r in rows})} documents)")


if __name__ == "__main__":
    main()
