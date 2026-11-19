"""Exploratory check: is the 2025 break in the historical series a vocabulary shift?

Held-out design (avoids picking words and testing them on the same texts):
  1. Discovery: find words over-represented in 2025 H1 (Jan-Jun) relative to
     2016-2022, using a smoothed log-ratio, minimum 15 occurrences in 2025 H1.
     Topic words (proper nouns, capitalised in the source) are excluded so the
     list captures style, not news events.
  2. Test: measure the rate of those words in 2025 H2 (Jul-Dec) and in every
     earlier year. 2025 H2 texts were never used to choose the words.

Exploratory only. A shift in wording does not show that AI tools were used by
authors or translators; topic changes and new drafting conventions are
alternative explanations. Run from the repository root:

    python scripts/explore_2025_shift.py
"""

from __future__ import annotations

import collections
import json
import math
import re
from pathlib import Path

CORPUS = Path("data/processed/motion_corpus.json")
WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def load() -> list[dict]:
    recs = json.loads(CORPUS.read_text(encoding="utf-8"))["records"]
    return [r for r in recs if r["exclusion_de"] is None and r["reference_de"]]


def half(r: dict) -> str:
    return "H1" if int(r["submission_date"][5:7]) <= 6 else "H2"


def counts(texts: list[str]) -> tuple[collections.Counter, collections.Counter]:
    lower, capital = collections.Counter(), collections.Counter()
    for t in texts:
        for w in WORD.findall(t):
            lower[w.lower()] += 1
            if w[0].isupper():
                capital[w.lower()] += 1
    return lower, capital


def discover(recs: list[dict], n_words: int = 30, min_count: int = 15) -> list[str]:
    disc = [r["reference_de"] for r in recs if r["year"] == 2025 and half(r) == "H1"]
    base = [r["reference_de"] for r in recs if 2016 <= r["year"] <= 2022]
    a, a_cap = counts(disc)
    b, _ = counts(base)
    na, nb = sum(a.values()), sum(b.values())
    scores = {}
    for w, k in a.items():
        # skip rare words and nouns/proper nouns (mostly capitalised in German): keeps style words
        if k < min_count or a_cap[w] / k > 0.5 or len(w) < 4:
            continue
        scores[w] = math.log((k + 1) / na) - math.log((b[w] + 1) / nb)
    return [w for w, _ in sorted(scores.items(), key=lambda x: -x[1])[:n_words]]


def rate(texts: list[str], markers: set[str]) -> tuple[float, float]:
    words = hits = docs2 = 0
    for t in texts:
        toks = [w.lower() for w in WORD.findall(t)]
        h = sum(w in markers for w in toks)
        words += len(toks)
        hits += h
        docs2 += h >= 2
    return 1000 * hits / words, 100 * docs2 / len(texts)


def main() -> None:
    recs = load()
    markers = discover(recs)
    print("Marker words chosen on 2025 H1 vs 2016-2022 (style words, not nouns):")
    print(", ".join(markers), "\n")
    print(f"{'period':<10}{'docs':>6}{'per 1000 words':>17}{'docs with >=2':>16}")
    groups = [(str(y), [r for r in recs if r["year"] == y]) for y in range(2010, 2025)]
    groups += [
        ("2025 H1*", [r for r in recs if r["year"] == 2025 and half(r) == "H1"]),
        ("2025 H2", [r for r in recs if r["year"] == 2025 and half(r) == "H2"]),
    ]
    for name, g in groups:
        per1000, share = rate([r["reference_de"] for r in g], set(markers))
        print(f"{name:<10}{len(g):>6}{per1000:>17.2f}{share:>15.1f}%")
    print(
        "\n* discovery sample: its value is inflated by construction. "
        "Compare 2025 H2 (held out) with earlier years."
    )


if __name__ == "__main__":
    main()
