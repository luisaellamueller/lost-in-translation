"""Exploratory source/target sentence counts; run from any working directory.

Uses spaCy language-specific tokenizers, without trained parsers. Applies the
existing punctuation/line-boundary rules and a punctuation-only sensitivity
analysis. Counts do not establish alignment, meaning preservation, or syntax.
"""

import json
import re
from pathlib import Path

import numpy as np
import spacy
from spacy.symbols import ORTH

from compare_complexity import paragraph_boundaries

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
FIELDS = {
    "source": "input_fr",
    "official": "reference_de",
    "generated": "translation_de",
}


def pipeline(language, texts):
    """Build a language-specific tokenizer with the shared boundary conventions."""
    nlp = spacy.blank(language)
    abbreviations = {"Art.", "art."}
    for text in texts:
        abbreviations.update(re.findall(r"\b\d+[a-z]+\.", text))
    for abbreviation in sorted(abbreviations):
        nlp.tokenizer.add_special_case(abbreviation, [{ORTH: abbreviation}])
    nlp.add_pipe("sentencizer", config={"punct_chars": [".", "!", "?"]})
    return nlp


def measure(nlp, text, lines):
    """Count nonpunctuation words and nonempty sentences, retaining audit text."""
    doc = nlp(text)
    if lines:
        paragraph_boundaries(doc)
    sentences = []
    for sentence in doc.sents:
        count = sum(not t.is_punct and not t.is_space for t in sentence)
        if count:
            sentences.append({"text": sentence.text.strip(), "words": count})
    words = sum(s["words"] for s in sentences)
    assert sentences and words
    return {
        "sentence_count": len(sentences),
        "word_count": words,
        "mean_sentence_words": words / len(sentences),
        "sentences": sentences,
    }


def summarize(records):
    """Compare absolute count gaps within each triple and bootstrap within year."""
    source = np.array([r["source"]["sentence_count"] for r in records])
    off = np.array([r["official"]["sentence_count"] for r in records])
    gen = np.array([r["generated"]["sentence_count"] for r in records])
    off_gap, gen_gap = abs(off - source), abs(gen - source)
    delta = gen_gap - off_gap
    # Resample whole paired documents within year; preserve the sampling design.
    years = np.array([r["year"] for r in records])
    groups = [np.flatnonzero(years == y) for y in np.unique(years)]
    rng = np.random.default_rng(48)
    boot = [
        float(delta[np.concatenate([rng.choice(g, len(g)) for g in groups])].mean())
        for _ in range(2000)
    ]
    result = {
        "n": len(records),
        "generated_closer": int(sum(gen_gap < off_gap)),
        "official_closer": int(sum(off_gap < gen_gap)),
        "equally_close": int(sum(gen_gap == off_gap)),
        "mean_absolute_gap_difference_generated_minus_official": float(delta.mean()),
        "year_stratified_paired_bootstrap_95_ci": np.quantile(
            boot, [0.025, 0.975]
        ).tolist(),
    }
    for version in FIELDS:
        counts = np.array([r[version]["sentence_count"] for r in records])
        result[version] = {
            "mean_sentence_count": float(counts.mean()),
            "mean_word_count": float(
                np.mean([r[version]["word_count"] for r in records])
            ),
            "mean_sentence_words": float(
                np.mean([r[version]["mean_sentence_words"] for r in records])
            ),
        }
        if version != "source":
            result[version].update(
                {
                    "exact_source_count_matches": int(sum(counts == source)),
                    "mean_absolute_sentence_count_gap": float(
                        abs(counts - source).mean()
                    ),
                    "mean_signed_sentence_count_gap": float((counts - source).mean()),
                    "mean_target_source_word_ratio": float(
                        np.mean(
                            [
                                r[version]["word_count"] / r["source"]["word_count"]
                                for r in records
                            ]
                        )
                    ),
                }
            )
    return result


def main():
    source = json.loads((DATA / "complexity_fr_author_translations.json").read_text())
    rows = source["records"]
    assert len({r["document_id"] for r in rows}) == len(rows)
    assert all(r["finish_reason"] == "stop" for r in rows)
    fr = pipeline("fr", [r["input_fr"] for r in rows])
    de = pipeline(
        "de", [r[f] for r in rows for f in ["reference_de", "translation_de"]]
    )
    output = {
        "input": "complexity_fr_author_translations.json",
        "spacy_version": spacy.__version__,
        "excluded_failure_ids": [
            r["document_id"] for r in source.get("failed_records", [])
        ],
        "limitations": [
            "Sentence-count equality does not establish matching boundaries, alignment, syntax or meaning.",
            "Language-specific tokenization and German compounding limit direct word-length comparisons.",
            "Rule-based segmentation can mishandle abbreviations and numbered lists.",
            "Bootstrap is exploratory, stratified by year, not adjusted for repeated authors or multiple testing.",
        ],
        "analyses": {},
    }
    for mode, lines in [("punctuation_and_lines", True), ("punctuation_only", False)]:
        records = []
        for r in rows:
            record = {"document_id": r["document_id"], "year": r["year"]}
            for version, field in FIELDS.items():
                record[version] = measure(
                    fr if version == "source" else de, r[field], lines
                )
            records.append(record)
        output["analyses"][mode] = {"summary": summarize(records), "records": records}
    saved = {
        r["document_id"]: r
        for r in json.loads((DATA / "complexity_fr_author_results.json").read_text())[
            "records"
        ]
    }
    mismatches = []
    for r in output["analyses"]["punctuation_and_lines"]["records"]:
        for version in ["official", "generated"]:
            for metric in ["sentence_count", "word_count"]:
                if r[version][metric] != saved[r["document_id"]][version][metric]:
                    mismatches.append(
                        {
                            "document_id": r["document_id"],
                            "version": version,
                            "metric": metric,
                            "new": r[version][metric],
                            "saved": saved[r["document_id"]][version][metric],
                        }
                    )
    output["german_counts_check_against_existing_results"] = mismatches
    (DATA / "source_structure_comparison.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    report = [
        "# Exploratory source-structure comparison",
        "",
        "259 completed French-source / official-German / generated-German triples. No new translations.",
        "",
        "Counts use language-specific spaCy tokenizers, .!? sentence boundaries, preserved Art./art. and digit-letter references. The primary analysis also starts sentences at nonempty lines, as in the existing German analysis.",
        "",
        "Negative paired gap differences mean the generated sentence count is closer to the source.",
        "",
    ]
    for mode, analysis in output["analyses"].items():
        s = analysis["summary"]
        report += [
            f"## {mode}",
            "",
            "| Measure | French | Official German | Generated German |",
            "|---|---:|---:|---:|",
        ]
        for metric in ["mean_sentence_count", "mean_word_count", "mean_sentence_words"]:
            report.append(
                "| "
                + metric
                + " | "
                + " | ".join(f"{s[v][metric]:.3f}" for v in FIELDS)
                + " |"
            )
        for metric in [
            "exact_source_count_matches",
            "mean_absolute_sentence_count_gap",
            "mean_target_source_word_ratio",
        ]:
            report.append(
                "| "
                + metric
                + " | — | "
                + " | ".join(f"{s[v][metric]:.3f}" for v in ["official", "generated"])
                + " |"
            )
        report += [
            "",
            f"Generated closer: {s['generated_closer']}; official closer: {s['official_closer']}; tied: {s['equally_close']}.",
            f"Paired mean absolute count-gap difference: {s['mean_absolute_gap_difference_generated_minus_official']:.3f}; exploratory 95% bootstrap CI: {s['year_stratified_paired_bootstrap_95_ci']}.",
            "",
        ]
    report += [
        "## Validation and limits",
        "",
        f"German count differences against saved results: {len(mismatches)}.",
        "",
    ]
    report += ["- " + x for x in output["limitations"]]
    report += [
        "",
        "## Inspected examples",
        "",
        "- 20003048: French and generated German have 8 sentences; official German has 7. The official text combines the first two French sentences; the generated text keeps them separate.",
        "- 20173849: French and generated German have 5 sentences; official German has 6. The official text separates the final reason into a sentence beginning Denn; the generated text keeps a da-clause.",
        "- 20013149: French and generated German have 4 sentences; official German has 5. The official text splits the first French sentence. The generated text also contains meaning/grammar problems: matching sentence count is not a quality guarantee.",
        "",
        "These are assistant spot-checks, not an independent human annotation study or a full boundary-alignment audit. Full segmented texts are in the JSON output.",
    ]
    report += [
        "",
        "Reproduce from the project root: `python scripts/compare_source_structure.py`.",
        "",
    ]
    (ROOT / "results" / "source_structure_comparison.md").write_text("\n".join(report))
    print(
        json.dumps({k: v["summary"] for k, v in output["analyses"].items()}, indent=2)
    )
    print("German count mismatches:", len(mismatches))


if __name__ == "__main__":
    main()
