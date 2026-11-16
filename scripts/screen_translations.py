"""Screening of the machine translations (French-authored sample).

Automatic checks on all completed outputs:
  * generation stopped normally and the text ends with sentence punctuation;
  * length ratio machine words / French words (and official / French for comparison);
  * share of frequent French function words in the output (> 5% is flagged);
  * repeated word 6-grams (more than 3 repeats is flagged).
Flagged texts were inspected by reading; the judgements are stored in
results/screening_annotations_french.csv (check = repetition_flag / french_flag).

Reading sample: 20 outputs drawn with random.Random(2026); the opening
(about 100 words) of each was read against the French source and judged
ok / minor (grammar or style, meaning intact) / content (meaning, number,
term or name wrong). The judgements are human annotations stored in the same
CSV (check = reading_sample); this script verifies that they cover exactly the
drawn sample and every flagged text, and counts them.

Run from the repository root:
    python scripts/screen_translations.py
Output: results/screening_french.md
"""
from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter
from pathlib import Path
from statistics import median

TRANSLATIONS = Path("data/processed/complexity_fr_author_translations.json")
ANNOTATIONS = Path("results/screening_annotations_french.csv")
FRENCH_WORDS = set("le la les des du de et est une un que qui dans pour par sur au aux pas ne nous il "
                   "elle ce cette ces son sa ses leur".split())
SAMPLE_SEED, SAMPLE_SIZE = 2026, 20


def main() -> None:
    data = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    recs = data["records"]
    stopped = sum(r["finish_reason"] == "stop" for r in recs)
    ends = sum(r["translation_de"].strip()[-1:] in '.!?»")“”:' for r in recs)
    ratio = [len(r["translation_de"].split()) / len(r["input_fr"].split()) for r in recs]
    off_ratio = [len(r["reference_de"].split()) / len(r["input_fr"].split()) for r in recs]
    french_flag, repeat_flag = [], []
    for r in recs:
        toks = re.findall(r"\w+", r["translation_de"].lower())
        if sum(t in FRENCH_WORDS for t in toks) / max(1, len(toks)) > 0.05:
            french_flag.append(str(r["document_id"]))
        grams = Counter(tuple(toks[i:i + 6]) for i in range(len(toks) - 5))
        if sum(c - 1 for c in grams.values() if c > 1) > 3:
            repeat_flag.append(str(r["document_id"]))

    sample = [str(r["document_id"]) for r in random.Random(SAMPLE_SEED).sample(recs, SAMPLE_SIZE)]
    with open(ANNOTATIONS, encoding="utf-8") as f:
        ann = list(csv.DictReader(f))
    by_check = {c: {a["document_id"]: a for a in ann if a["check"] == c}
                for c in ("reading_sample", "repetition_flag", "french_flag")}
    for check, expected in (("reading_sample", sample), ("repetition_flag", repeat_flag), ("french_flag", french_flag)):
        if set(by_check[check]) != set(expected):
            raise SystemExit(f"Annotations for {check} do not match the texts drawn/flagged: "
                             f"missing {sorted(set(expected) - set(by_check[check]))}, "
                             f"extra {sorted(set(by_check[check]) - set(expected))}")
    judged = Counter(a["judgement"] for a in by_check["reading_sample"].values())

    lines = [
        "# Screening of the machine translations (French-authored sample)", "",
        f"Completed outputs: {len(recs)}; failed (output limit): {len(data['failed_records'])}.", "",
        "## Automatic checks", "",
        f"- Stopped normally: {stopped} of {len(recs)}; end with sentence punctuation: {ends} of {len(recs)}.",
        f"- Length ratio machine/French words: {min(ratio):.2f}-{max(ratio):.2f} (median {median(ratio):.2f}); "
        f"official/French median {median(off_ratio):.2f}.",
        f"- French function-word share > 5%: {len(french_flag)} ({', '.join(french_flag) or '-'}).",
        f"- Repeated 6-grams (> 3 repeats): {len(repeat_flag)} ({', '.join(repeat_flag)}).",
        "", "Inspection of flagged texts (annotations):", "",
    ]
    for check in ("repetition_flag", "french_flag"):
        for d, a in sorted(by_check[check].items()):
            lines.append(f"- {d} ({check}): {a['judgement']}. {a['note']}")
    lines += ["", f"## Reading sample (random.Random({SAMPLE_SEED}), {SAMPLE_SIZE} texts, opening ~100 words)", "",
              f"- ok: {judged['ok']}; minor: {judged['minor']}; content-changing: {judged['content']}", ""]
    for d in sample:
        a = by_check["reading_sample"][d]
        lines.append(f"- {d}: {a['judgement']}" + (f". {a['note']}" if a["note"] else ""))
    Path("results/screening_french.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
