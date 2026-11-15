"""Consistency checks for the bundled data. Run from the repository root:

    python scripts/check_data.py

Prints PASS / WARN / FAIL per check and ends with a summary. It reads the
saved files only; nothing is downloaded or overwritten.
"""
from __future__ import annotations

import collections
import gzip
import json
import math
import re
import statistics as st
import unicodedata
from pathlib import Path

PROC, RAW = Path("data/processed"), Path("data/raw")
RESULTS: list[tuple[str, str, str]] = []


def report(status: str, name: str, detail: str = "") -> None:
    RESULTS.append((status, name, detail))
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def check(cond: bool, name: str, detail: str = "", warn: bool = False) -> None:
    report("PASS" if cond else ("WARN" if warn else "FAIL"), name, detail)


def load(name: str):
    path = PROC / name
    opener = gzip.open if name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def as_dict(v):
    """Some nested measurements are stored as dicts, some as their repr strings."""
    if isinstance(v, dict):
        return v
    import ast
    return ast.literal_eval(v)


FR_WORDS = {"le", "la", "les", "des", "est", "et", "une", "pour", "dans", "que", "qui", "pas", "sur", "du"}
DE_WORDS = {"der", "die", "das", "und", "ist", "nicht", "mit", "für", "von", "zu", "den", "ein", "eine", "auf"}
EN_WORDS = {"the", "and", "of", "to", "is", "that", "for", "with", "this", "are"}


def lang_share(text: str, words: set[str]) -> float:
    toks = re.findall(r"[a-zäöüéèàç]+", text.lower())
    return sum(t in words for t in toks) / max(len(toks), 1)


def max_ngram_repeat(text: str, n: int = 8) -> int:
    toks = text.split()
    grams = collections.Counter(tuple(toks[i:i + n]) for i in range(len(toks) - n + 1))
    return max(grams.values(), default=0)


# ---------------------------------------------------------------- corpus
def check_corpus():
    print("\n== 1. Corpus (motion_corpus.json)")
    recs = load("motion_corpus.json")["records"]
    ids = [str(r["document_id"]) for r in recs]
    check(len(recs) == 10622, "record count", f"{len(recs)} (handover: 10,622)")
    check(len(set(ids)) == len(ids), "unique document IDs", f"{len(ids) - len(set(ids))} duplicates")
    years = collections.Counter(int(r["year"]) for r in recs)
    check(min(years) == 2000 and max(years) == 2025 and len(years) == 26, "years 2000–2025, none missing")

    bad_year = [r for r in recs if str(r["submission_date"])[:4] != str(r["year"])]
    check(not bad_year, "year field matches submission date", f"{len(bad_year)} mismatches")
    id_year = [r for r in recs if str(r["document_id"])[:4] != str(r["year"])]
    check(len(id_year) < 0.02 * len(recs), "ID prefix matches submission year",
          f"{len(id_year)} differ (business numbers can be assigned in a later year)", warn=True)

    excl = collections.Counter(r["exclusion_de"] for r in recs if r["exclusion_de"] is not None)
    elig = [r for r in recs if r["exclusion_de"] is None and r["reference_de"]]
    check(len(elig) == 10581, "eligible German texts", f"{len(elig)} (handover: 10,581)")
    check(sum(excl.values()) == 41, "German exclusions", f"{sum(excl.values())}: {dict(excl)}")

    pairs = [r for r in elig if r["input_fr"] and r["exclusion_fr"] is None]
    check(len(pairs) == 10573, "eligible DE–FR pairs", f"{len(pairs)} (handover: 10,573)")

    html = [r for r in elig if re.search(r"<[a-zA-Z/][^>]*>|&[a-z]+;|&#\d+;", r["reference_de"])]
    check(not html, "no HTML tags/entities left in German texts", f"{len(html)} texts")

    same = [r for r in pairs if r["reference_de"].strip() == r["input_fr"].strip()]
    check(not same, "German ≠ French text (not untranslated copies)", f"{len(same)} identical")

    de_is_fr = [r["document_id"] for r in elig if lang_share(r["reference_de"], FR_WORDS) > lang_share(r["reference_de"], DE_WORDS)]
    check(not de_is_fr, "German field looks German", f"{len(de_is_fr)} look French: {de_is_fr[:5]}", warn=True)
    fr_is_de = [r["document_id"] for r in pairs if lang_share(r["input_fr"], DE_WORDS) > lang_share(r["input_fr"], FR_WORDS)]
    check(not fr_is_de, "French field looks French", f"{len(fr_is_de)} look German: {fr_is_de[:5]}", warn=True)

    lens = sorted(len(r["reference_de"].split()) for r in elig)
    short = sum(n < 20 for n in lens)
    check(short < 0.02 * len(lens), "few very short German texts (<20 words)", f"{short} texts; median {lens[len(lens)//2]}, max {lens[-1]} words", warn=True)

    # decomposed umlauts (u + combining diaeresis) are tokenised differently from ü
    nfd = collections.Counter(int(r["year"]) for r in elig if unicodedata.normalize("NFC", r["reference_de"]) != r["reference_de"])
    check(sum(nfd.values()) < 50, "Unicode normalisation (NFC)", f"{sum(nfd.values())} texts not NFC, by year: {dict(sorted(nfd.items()))}", warn=True)

    dup = collections.Counter(r["reference_de"].strip() for r in elig)
    extra = sum(c - 1 for c in dup.values() if c > 1)
    groups = sum(1 for c in dup.values() if c > 1)
    check(groups == 246 and extra == 316, "identical German texts across IDs",
          f"{groups} groups / {extra} extra copies (handover: 246 / 316)", warn=True)
    return recs, elig


def check_coverage(recs):
    print("\n== 2. Raw pages vs coverage audit")
    cov = {y["year"]: y for y in load("motion_coverage.json")["years"]}
    raw_counts = collections.Counter()
    for p in RAW.glob("motions_*_*_offset_*.json"):
        if p.name.endswith(".metadata.json"):
            continue
        _, year, lang, *_ = p.stem.split("_")
        data = json.loads(p.read_text(encoding="utf-8"))
        d = data.get("d", data) if isinstance(data, dict) else data
        rows = d.get("results", d) if isinstance(d, dict) else d
        raw_counts[(int(year), lang)] += len(rows)
    bad = [(y, l, n, cov[y][f"{l}_records"]) for (y, l), n in raw_counts.items() if n != cov[y][f"{l}_records"]]
    check(not bad, "raw rows per year/language = coverage audit", f"mismatches: {bad[:5]}")
    per_year = collections.Counter(int(r["year"]) for r in recs)
    # the corpus keeps only motions with a nonempty German justification
    bad2 = [(y, per_year[y], c["de_with_justification"]) for y, c in cov.items() if per_year[y] != c["de_with_justification"]]
    check(not bad2, "corpus records per year = motions with a German justification", f"mismatches: {bad2[:5]}")


# ---------------------------------------------------------------- historical
def check_historical(elig):
    print("\n== 3. Historical scores (historical_complexity.json.gz)")
    h = load("historical_complexity.json.gz")
    recs = h["records"]
    check(len(recs) == len(elig), "one score record per eligible text", f"{len(recs)} vs {len(elig)}")
    check({str(r["document_id"]) for r in recs} == {str(r["document_id"]) for r in elig}, "same IDs as eligible corpus")

    by_year = collections.defaultdict(list)
    for r in recs:
        by_year[int(r["year"])].append(as_dict(r["official"]))
    worst = 0.0
    for y in h["years"]:
        for metric, s in y["metrics"].items():
            vals = [m[metric] for m in by_year[y["year"]] if m.get(metric) is not None]
            if vals:
                worst = max(worst, abs(st.mean(vals) - s["mean"]))
            if len(vals) != s["available_documents"]:
                report("FAIL", "metric N", f"{y['year']} {metric}: {len(vals)} vs {s['available_documents']}")
    check(worst < 1e-9, "yearly means recompute from document records", f"max abs difference {worst:.2e}")

    issues = []
    for r in recs:
        m = as_dict(r["official"])
        for k in ("mattr_25", "mattr_50"):
            if m.get(k) is not None and not 0 < m[k] <= 1:
                issues.append((r["document_id"], k, m[k]))
        for k, v in m.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                issues.append((r["document_id"], k, v))
        if m.get("word_count", 1) <= 0:
            issues.append((r["document_id"], "word_count", m["word_count"]))
    check(not issues, "values in valid ranges (MATTR in (0,1], no NaN/inf, words > 0)", f"{len(issues)} problems: {issues[:3]}")

    na = sum(as_dict(r["official"]).get("mattr_50") is None for r in recs)
    check(na == 149, "MATTR50 unavailable only for short texts", f"{na} missing (handover: 149)", warn=True)

    # extreme outliers per metric (|z| > 6) — inspect, not necessarily wrong
    metrics = ["mean_sentence_words", "mean_content_word_zipf", "lix", "mean_sentence_tree_depth"]
    outl = {}
    for k in metrics:
        vals = [(r["document_id"], as_dict(r["official"])[k]) for r in recs if as_dict(r["official"]).get(k) is not None]
        mu, sd = st.mean(v for _, v in vals), st.pstdev(v for _, v in vals)
        outl[k] = [(i, round(v, 1)) for i, v in vals if abs(v - mu) > 6 * sd][:4]
    n_out = sum(len(v) for v in outl.values())
    check(n_out == 0, "no extreme outliers (|z|>6)", f"{outl}", warn=True)


# ---------------------------------------------------------------- sample + translations
def check_sample_and_translations(recs):
    print("\n== 4. Translation sample, outputs and paired results")
    corpus = {str(r["document_id"]): r for r in recs}
    pairs = load("complexity_expanded_pairs.json")
    sample = pairs["records"]
    years = collections.Counter(int(r["year"]) for r in sample)
    check(len(sample) == 260 and set(years.values()) == {10}, "260 pairs, 10 per year")
    excluded = {str(i) for i in pairs["excluded_development_ids"]}
    check(not ({str(r["document_id"]) for r in sample} & excluded), "no overlap with the 30 development IDs")
    mism = [r["document_id"] for r in sample
            if corpus[str(r["document_id"])]["input_fr"] != r["input_fr"]
            or corpus[str(r["document_id"])]["reference_de"] != r["reference_de"]]
    check(not mism, "sample texts identical to corpus", f"{len(mism)} differ")

    tr = load("complexity_expanded_translations.json")
    done, failed = tr["records"], tr["failed_records"]
    ids_tr = {str(r["document_id"]) for r in done + failed}
    check(ids_tr == {str(r["document_id"]) for r in sample}, "translations cover exactly the sample",
          f"{len(done)} completed + {len(failed)} failed")
    check(all(r["finish_reason"] == "stop" for r in done), "all completed outputs stopped normally")
    changed = [r["document_id"] for r in done if r["input_fr"] != corpus[str(r["document_id"])]["input_fr"]]
    check(not changed, "model inputs identical to corpus French", f"{len(changed)} differ")

    # --- quick generation screening (Klara's open to-do; these are flags, not verdicts)
    print("   -- screening of the 259 outputs (flags to inspect by hand)")
    flags = collections.defaultdict(list)
    for r in done:
        t, ref, src = r["translation_de"], r["reference_de"], r["input_fr"]
        i = str(r["document_id"])
        ratio = len(t.split()) / max(len(ref.split()), 1)
        if ratio < 0.7 or ratio > 1.4:
            flags["length ratio vs official outside 0.7–1.4"].append((i, round(ratio, 2)))
        rep_t, rep_ref = max_ngram_repeat(t), max_ngram_repeat(src)
        if rep_t >= 3 and rep_t > rep_ref:
            flags["repeated 8-word sequence (≥3×, more than in source)"].append((i, rep_t))
        if lang_share(t, FR_WORDS) > 0.05:
            flags["French words left in output (>5%)"].append((i, round(lang_share(t, FR_WORDS), 2)))
        if lang_share(t, EN_WORDS) > 0.03:
            flags["English in output (>3%)"].append((i, round(lang_share(t, EN_WORDS), 2)))
        if re.search(r"(?i)übersetzung|translation|hier ist|here is", t[:120]):
            flags["meta text at start ('Hier ist die Übersetzung…')"].append(i)
        if t.strip() and t.strip()[-1] not in ".!?»«\")…:":
            if src.strip()[-1] in ".!?»«\")…:":
                flags["output ends without final punctuation (source has it)"].append(i)
        if t.count("\n") + 1 < 0.5 * (src.count("\n") + 1) and src.count("\n") >= 3:
            flags["paragraph structure lost (<50% of source line breaks)"].append(i)
    total = len({x if isinstance(x, str) else x[0] for v in flags.values() for x in v})
    check(total == 0, "generation screening", f"{total} of {len(done)} outputs flagged at least once", warn=True)
    for k, v in flags.items():
        print(f"      {k}: {len(v)}  e.g. {v[:4]}")

    res = load("complexity_expanded_results.json")
    check({str(r["document_id"]) for r in res["records"]} == {str(r["document_id"]) for r in done},
          "paired results cover exactly the 259 completed outputs")
    worst = 0.0
    for metric, s in res["summary"].items():
        diffs = [as_dict(r["generated"])[metric] - as_dict(r["official"])[metric] for r in res["records"]
                 if as_dict(r["generated"]).get(metric) is not None and as_dict(r["official"]).get(metric) is not None]
        md = s.get("mean_difference", s.get("difference"))
        if md is not None and diffs:
            worst = max(worst, abs(st.mean(diffs) - md))
    check(worst < 1e-9, "paired mean differences recompute from records", f"max abs difference {worst:.2e}", warn=True)
    return flags


def main():
    recs, elig = check_corpus()
    check_coverage(recs)
    check_historical(elig)
    check_sample_and_translations(recs)
    c = collections.Counter(s for s, _, _ in RESULTS)
    print(f"\nSummary: {c['PASS']} pass, {c['WARN']} warn, {c['FAIL']} fail")


if __name__ == "__main__":
    main()
