"""RQ2 terminology: are Swiss parliamentary terms and abbreviations kept?

For every French source text that names a parliamentary instrument or
institution, we check whether the official and the machine German contain the
Swiss German term, and if the machine output does not, which word it uses
instead. The rules below were written after reading every occurrence in
context (see results/terminology_contexts_french.csv, which this script also
writes so the decisions can be inspected):

  * a text counts as "kept" if the Swiss term (any inflected or derived form,
    e.g. Motionen, Motionär) appears in that German version;
  * otherwise the machine rendering is the first matching alternative listed
    for that term; texts without any alternative are "other" (motion) or
    "lost" (interpellation: the sentence was dropped or mistranslated).

French abbreviations of Swiss authorities and laws (e.g. AVS for AHV) count as
"kept in French" when the French form appears and the German one does not.

Run from the repository root:
    python scripts/terminology_check.py
Outputs: results/terminology_french.md         (Table 1 and the abbreviation count)
         results/terminology_checked_french.csv (one row per text and term)
         results/terminology_contexts_french.csv (French and German sentences, for inspection)
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

TRANSLATIONS = Path("data/processed/complexity_fr_author_translations.json")
OUT = Path("results")

# term: (French pattern, Swiss German pattern, [(alternative label, pattern)], fallback label)
TERMS = {
    "motion": (r"\bmotions?\b", r"\bMotion\w*", [("Antrag", r"\bAntr(ag|äg)\w*")], "other"),
    "interpellation": (r"\binterpellations?\b", r"\bInterpellation\w*", [("Anfrage", r"\bAnfrage\w*")], "lost"),
    "postulat": (r"\bpostulats?\b", r"\bPostulat\w*",
                 [("Petition", r"\bPetition\w*"), ("Punkt", r"\bPunkt\b"), ("Prämisse", r"\bPrämisse\b")], "other"),
    "initiative parlementaire": (r"\binitiatives? parlementaires?\b", r"\bInitiative\w*", [], "other"),
    "Conseil fédéral": (r"\bconseil f[ée]d[ée]ral\b", r"\bBundesrat\w*", [("Bundesregierung", r"\bBundesregierung\w*")], "other"),
    "Conseil national": (r"\bconseil national\b", r"\bNationalrat\w*", [], "other"),
    "Conseil des Etats": (r"\bconseil des [ée]tats\b", r"\bStänderat\w*", [("Rat der Stände", r"\bRat der Stände\b")], "other"),
}
# French abbreviation -> Swiss German abbreviation (unambiguous forms only)
ABBREVIATIONS = {
    "AVS": "AHV", "LAMal": "KVG", "LPP": "BVG", "LIFD": "DBG", "LHID": "StHG", "CFF": "SBB", "EPF": "ETH",
    "OFSP": "BAG", "OFEV": "BAFU", "OFAS": "BSV", "LCR": "SVG", "DFAE": "EDA", "DDPS": "VBS", "DETEC": "UVEK",
    "OFROU": "ASTRA", "LAA": "UVG", "APG": "EO", "OFEN": "BFE", "OFT": "BAV", "LPE": "USG", "LAT": "RPG",
    "OFAG": "BLW", "AFC": "ESTV", "CDF": "EFK", "LAI": "IVG", "LAVS": "AHVG", "OFS": "BFS", "OFJ": "BJ",
    "DFF": "EFD", "DFI": "EDI", "DEFR": "WBF", "DFJP": "EJPD", "CEDH": "EMRK", "LACI": "AVIG",
}


def machine_rendering(term: str, german: str) -> str:
    """Return "kept" if the Swiss term appears in the German text, else the alternative used."""
    _, de_pat, alternatives, fallback = TERMS[term]
    if re.search(de_pat, german):
        return "kept"
    return next((label for label, p in alternatives if re.search(p, german)), fallback)


def keeps_french_abbreviation(abbreviation: str, german: str) -> bool:
    """True if the French abbreviation appears in the German text and the Swiss German one does not."""
    return bool(re.search(rf"\b{abbreviation}\b", german)) and not re.search(
        rf"\b{ABBREVIATIONS[abbreviation]}\b", german)


def sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text)


def main() -> None:
    records = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))["records"]
    rows, contexts = [], []
    lines = ["# RQ2: parliamentary terminology (French-authored sample, 259 pairs)", "",
             "| French source | Texts | Official keeps | Machine keeps | Machine instead (texts) |",
             "|---|---:|---:|---:|---|"]
    for term, (fr_pat, de_pat, alternatives, fallback) in TERMS.items():
        docs = [r for r in records if re.search(fr_pat, r["input_fr"], re.I)]
        off_keep = mt_keep = 0
        instead = Counter()
        for r in docs:
            off = bool(re.search(de_pat, r["reference_de"]))
            mt = bool(re.search(de_pat, r["translation_de"]))
            rendering = machine_rendering(term, r["translation_de"])
            off_keep += off
            mt_keep += mt
            if not mt:
                instead[rendering] += 1
            rows.append({"term": term, "document_id": r["document_id"], "official_keeps": int(off),
                         "machine_keeps": int(mt), "machine_rendering": rendering})
            contexts.append({"term": term, "document_id": r["document_id"],
                             "french": " | ".join(s for s in sentences(r["input_fr"]) if re.search(fr_pat, s, re.I)),
                             "official": " | ".join(s for s in sentences(r["reference_de"]) if re.search(de_pat, s)),
                             "machine": r["translation_de"] if not mt else
                             " | ".join(s for s in sentences(r["translation_de"]) if re.search(de_pat, s))})
        alt = ", ".join(f"{k} ({v})" for k, v in instead.most_common()) or "-"
        lines.append(f"| {term} | {len(docs)} | {off_keep} | {mt_keep} | {alt} |")

    # Abbreviations
    with_abbr = mt_french = off_french = 0
    examples = Counter()
    for r in records:
        found = [a for a in ABBREVIATIONS if re.search(rf"\b{a}\b", r["input_fr"])]
        if not found:
            continue
        with_abbr += 1
        keeps = lambda text: [a for a in found if keeps_french_abbreviation(a, text)]
        mt_list, off_list = keeps(r["translation_de"]), keeps(r["reference_de"])
        mt_french += bool(mt_list)
        off_french += bool(off_list)
        examples.update(mt_list)
    lines += ["", f"French abbreviations of Swiss authorities and laws: {with_abbr} texts contain one; "
              f"the machine output keeps the French form in {mt_french}, the official translation in {off_french}.",
              "Most frequent: " + ", ".join(f"{a}->{ABBREVIATIONS[a]} ({n})" for a, n in examples.most_common(8)) + "."]

    OUT.mkdir(exist_ok=True)
    (OUT / "terminology_french.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, data in (("terminology_checked_french.csv", rows), ("terminology_contexts_french.csv", contexts)):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
