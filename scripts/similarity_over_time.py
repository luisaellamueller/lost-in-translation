"""Finding 3: are official translations becoming more similar to machine output?

Idea (post-editing research, e.g. Toral 2019): a translator who starts from
machine output leaves its "footprint" in the final text. If machine translation
is increasingly used in the official workflow, official translations should
become more similar to machine output of the same source over time.

Metric (fixed before looking at the result): sentence-level chrF between the
official German translation and TranslateGemma's German translation of the same
French original, per document, on the French-authored sample. BLEU is reported
as a robustness check. Scores computed with sacrebleu (default settings).

Caveat: a rising similarity is also expected if the model saw recent official
translations during training. The data cannot separate the two explanations.

Run from the repository root:
    python scripts/similarity_over_time.py
Outputs: results/similarity_over_time.csv, results/similarity_over_time.md,
         docs/figures/similarity_over_time.png
"""
from __future__ import annotations

import csv
import json
import random
import statistics as st
from pathlib import Path

import sacrebleu

TRANSLATIONS = Path("data/processed/complexity_fr_author_translations.json")
PERIODS = [(2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2022), (2023, 2025)]
N_BOOT, SEED = 2000, 47


def bootstrap_ci(values: list[float], stat=st.mean) -> tuple[float, float]:
    rng = random.Random(SEED)
    boots = sorted(stat(rng.choices(values, k=len(values))) for _ in range(N_BOOT))
    return boots[int(0.025 * N_BOOT)], boots[int(0.975 * N_BOOT) - 1]


def slope(points: list[tuple[int, float]]) -> float:
    mx = st.mean(x for x, _ in points)
    my = st.mean(y for _, y in points)
    return sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x, _ in points)


def main() -> None:
    records = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))["records"]  # completed outputs only
    rows = []
    for r in records:
        rows.append({
            "document_id": r["document_id"], "year": int(r["year"]),
            "chrf": sacrebleu.sentence_chrf(r["translation_de"], [r["reference_de"]]).score,
            "bleu": sacrebleu.sentence_bleu(r["translation_de"], [r["reference_de"]]).score,
        })
    out = Path("results")
    out.mkdir(exist_ok=True)
    with open(out / "similarity_over_time.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    table = []
    for a, b in PERIODS:
        g = [r for r in rows if a <= r["year"] <= b]
        c = [r["chrf"] for r in g]
        lo, hi = bootstrap_ci(c)
        table.append({"period": f"{a}-{b}", "n": len(g), "chrf": st.mean(c), "lo": lo, "hi": hi,
                      "bleu": st.mean(r["bleu"] for r in g)})

    pts = [(r["year"], r["chrf"]) for r in rows]
    s = slope(pts)
    rng = random.Random(SEED)
    boots = sorted(slope(rng.choices(pts, k=len(pts))) for _ in range(N_BOOT))
    trend = (10 * s, 10 * boots[int(0.025 * N_BOOT)], 10 * boots[int(0.975 * N_BOOT) - 1])

    lines = ["# Similarity of official translations to machine output", "",
             f"French-authored sample, {len(rows)} completed pairs. chrF/BLEU: machine vs official German "
             f"(sacrebleu, sentence level). 95% intervals: {N_BOOT} document bootstrap resamples, seed {SEED}.", "",
             "| Period | Texts | chrF | 95% CI | BLEU |", "|---|---:|---:|---|---:|"]
    lines += [f"| {t['period']} | {t['n']} | {t['chrf']:.1f} | [{t['lo']:.1f}, {t['hi']:.1f}] | {t['bleu']:.1f} |"
              for t in table]
    lines += ["", f"Linear trend: {trend[0]:+.2f} chrF per decade, 95% CI [{trend[1]:+.2f}, {trend[2]:+.2f}].",
              "", "A rising similarity is consistent with increasing machine-translation use, but also with "
              "the model having seen recent official translations during training."]
    (out / "similarity_over_time.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    x = list(range(len(table)))
    ax.errorbar(x, [t["chrf"] for t in table],
                yerr=[[t["chrf"] - t["lo"] for t in table], [t["hi"] - t["chrf"] for t in table]],
                fmt="o-", color="#1f5f8b", capsize=3, lw=1.5, ms=5, label="chrF (left axis)")
    ax.set_xticks(x, [f"{t['period']}\n(n={t['n']})" for t in table], fontsize=8)
    ax.set_ylabel("chrF, official vs machine", fontsize=8.5)
    ax.tick_params(axis="y", labelsize=8)
    ax2 = ax.twinx()
    ax2.plot(x, [t["bleu"] for t in table], "s--", color="#b0b0b0", ms=4, lw=1, label="BLEU (right axis)")
    ax2.set_ylabel("BLEU", fontsize=8.5, color="#777777")
    ax2.tick_params(axis="y", labelsize=8, colors="#777777")
    for a in (ax, ax2):
        a.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper left", frameon=False)
    fig.tight_layout()
    Path("docs/figures").mkdir(parents=True, exist_ok=True)
    fig.savefig("docs/figures/similarity_over_time.png", dpi=220)


if __name__ == "__main__":
    main()
