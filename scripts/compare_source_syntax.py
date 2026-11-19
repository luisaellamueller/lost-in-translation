"""Exploratory source/target syntax associations, not cross-language tree matching.

Install requirements.txt, then run python scripts/compare_source_syntax.py.
French UD and German TIGER-derived dependency schemes differ. Correlations measure
text-level covariation, not aligned construction preservation or causation.
"""

import json
from pathlib import Path
import re
import numpy as np
import spacy
from spacy.symbols import ORTH
from compare_complexity import load_parser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
FIELDS = {
    "source": "input_fr",
    "official": "reference_de",
    "generated": "translation_de",
}
METRICS = [
    "mean_sentence_tree_depth",
    "mean_dependency_distance",
    "relative_clauses_per_sentence",
]


def measure(doc, lang):
    """Measure parsed structure; relative labels differ across the two languages."""
    sentences, distances, relatives = [], [], []
    for sent in doc.sents:
        words = [t for t in sent if not t.is_punct and not t.is_space]
        if not words:
            continue
        positions = {t.i: i for i, t in enumerate(words)}
        depth = max(
            sum(not a.is_punct and not a.is_space for a in t.ancestors) for t in words
        )
        distances.extend(
            abs(positions[t.i] - positions[t.head.i])
            for t in words
            if t.head.i in positions and t.head != t
        )
        clauses = [t for t in sent if t.dep_ == ("acl:relcl" if lang == "fr" else "rc")]
        relatives.extend(
            {"head": t.text, "subtree": " ".join(w.text for w in t.subtree)}
            for t in clauses
        )
        sentences.append(
            {
                "text": sent.text.strip(),
                "words": len(words),
                "tree_depth": depth,
                "relative_clauses": len(clauses),
            }
        )
    return {
        "sentence_count": len(sentences),
        "mean_sentence_words": float(np.mean([s["words"] for s in sentences])),
        "mean_sentence_tree_depth": float(
            np.mean([s["tree_depth"] for s in sentences])
        ),
        "mean_dependency_distance": float(np.mean(distances)),
        "relative_clause_count": len(relatives),
        "relative_clauses_per_sentence": len(relatives) / len(sentences),
        "relative_clauses": relatives,
        "sentences": sentences,
    }


def corr(a, b):
    """Return Pearson correlation for two nonconstant document-level arrays."""
    return float(np.corrcoef(a, b)[0, 1])


def residual(values, length):
    """Remove the fitted linear association with sentence length, including intercept."""
    design = np.column_stack([np.ones(len(length)), length])
    return values - design @ np.linalg.lstsq(design, values, rcond=None)[0]


def associations(records, metric, adjusted=False):
    """Compare dependent correlations using paired, year-stratified resampling.

    Each draw keeps source and both target versions together. When requested,
    length regressions are fitted again inside each bootstrap draw.
    """
    a = {v: np.array([r[v][metric] for r in records]) for v in FIELDS}
    lengths = {
        v: np.array([r[v]["mean_sentence_words"] for r in records]) for v in FIELDS
    }

    def calculate(indices):
        values = {
            v: (
                residual(a[v][indices], lengths[v][indices])
                if adjusted
                else a[v][indices]
            )
            for v in FIELDS
        }
        off = corr(values["source"], values["official"])
        gen = corr(values["source"], values["generated"])
        return off, gen, gen - off

    years = np.array([r["year"] for r in records])
    groups = [np.flatnonzero(years == y) for y in np.unique(years)]
    rng = np.random.default_rng(49)
    boot = np.array(
        [
            calculate(np.concatenate([rng.choice(g, len(g)) for g in groups]))
            for _ in range(2000)
        ]
    )
    off, gen, diff = calculate(np.arange(len(records)))
    return {
        "source_official_r": off,
        "source_generated_r": gen,
        "difference_generated_minus_official": diff,
        "difference_bootstrap_95_ci": np.quantile(boot[:, 2], [0.025, 0.975]).tolist(),
    }


def main():
    rows = json.loads((DATA / "complexity_fr_author_translations.json").read_text())[
        "records"
    ]
    if len({r["document_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate document IDs in completed sample")
    if any(r["finish_reason"] != "stop" for r in rows):
        raise ValueError("Incomplete translation in completed sample")
    de = load_parser([r[f] for r in rows for f in ["reference_de", "translation_de"]])
    fr = spacy.load("fr_core_news_sm", disable=["ner"])
    abbreviations = {"Art.", "art."}
    for r in rows:
        abbreviations.update(re.findall(r"\b\d+[a-z]+\.", r["input_fr"]))
    for a in sorted(abbreviations):
        fr.tokenizer.add_special_case(a, [{ORTH: a}])
    fr.add_pipe("sentencizer", before="parser", config={"punct_chars": [".", "!", "?"]})
    fr.add_pipe("paragraph_boundaries", before="parser")
    records = [{"document_id": r["document_id"], "year": r["year"]} for r in rows]
    for v, field in FIELDS.items():
        nlp = fr if v == "source" else de
        for r, doc in zip(
            records, nlp.pipe((row[field] for row in rows), batch_size=16)
        ):
            r[v] = measure(doc, "fr" if v == "source" else "de")
        print("Parsed", v, flush=True)
    saved = {
        r["document_id"]: r
        for r in json.loads((DATA / "complexity_fr_author_results.json").read_text())[
            "records"
        ]
    }
    for r in records:
        for v in ["official", "generated"]:
            for m in [
                "sentence_count",
                "mean_sentence_words",
                "mean_sentence_tree_depth",
                "mean_dependency_distance",
            ]:
                assert np.isclose(r[v][m], saved[r["document_id"]][v][m]), (
                    r["document_id"],
                    v,
                    m,
                )
    summaries = {
        m: {
            "raw": associations(records, m),
            "length_adjusted": associations(records, m, True),
        }
        for m in METRICS
    }
    output = {
        "n": len(records),
        "spacy_version": spacy.__version__,
        "parsers": {
            v: {"version": n.meta["version"], "sources": n.meta["sources"]}
            for v, n in [("fr_core_news_sm", fr), ("de_core_news_sm", de)]
        },
        "definitions": {
            "depth": "Mean sentence maximum nonpunctuation ancestor count, root=0.",
            "distance": "Mean absolute word-position distance for nonroot, nonpunctuation dependency edges.",
            "relatives": "Parser-labelled relative clause heads: French acl:relcl, German rc, per sentence. Different from existing POS-based relative-marker metric.",
            "adjustment": "Within each language/version, regress each metric on its own mean sentence length with intercept; correlate residuals. Refit on every bootstrap sample.",
            "uncertainty": "2000 paired document bootstrap draws within year, seed49. No author clustering or multiplicity adjustment.",
        },
        "summary": summaries,
        "records": records,
    }
    (DATA / "source_syntax_comparison.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    report = [
        "# Exploratory source–target syntax associations",
        "",
        "259 completed triples. Existing German depth/distance/length results reproduced exactly (numeric tolerance).",
        "",
        "French: fr_core_news_sm 3.8.0 (UD Sequoia). German: de_core_news_sm 3.8.0 (TIGER/Tiger2Dep). Different annotation schemes prevent interpreting raw cross-language depth gaps as structural preservation.",
        "",
        "| Measure | Source–official r | Source–model r | Difference [95% exploratory CI] |",
        "|---|---:|---:|---|",
    ]
    for m, s in summaries.items():
        for label in ["raw", "length_adjusted"]:
            a = s[label]
            lo, hi = a["difference_bootstrap_95_ci"]
            report.append(
                f"| {m} ({label}) | {a['source_official_r']:.3f} | {a['source_generated_r']:.3f} | {a['difference_generated_minus_official']:+.3f} [{lo:+.3f}, {hi:+.3f}] |"
            )
    report += [
        "",
        "## Interpretation limits",
        "",
        "- Correlations describe document-level covariation, not sentence-aligned syntactic equivalence or causality.",
        "- Length adjustment removes a fitted linear association with mean sentence length separately in each version; it does not remove every confound.",
        "- Relative-clause counts use dependency labels, not the existing relative-pronoun marker counts; parser conventions/errors may differ.",
        "- Exploratory intervals resample paired documents within year; repeated authors and multiple comparisons are not accounted for.",
        "- Automatic analyses require spot-checking; equal clause counts can conceal changed constructions or meanings.",
        "",
        "## Assistant spot-checks",
        "",
        "- 20173849: the French parser reports zero relative clauses despite the final sentence containing a relative clause introduced by dont. This is a false negative; do not treat these counts as gold-standard annotations.",
        "- 20073700: dependency-based counting identifies both official German relative clauses, including the one missed by the existing POS-marker measure. These are distinct operationalizations, not interchangeable counts.",
        "- These checks are illustrative, not an independent human audit.",
        "",
        "Reproduce: `python scripts/compare_source_syntax.py` (install `requirements.txt`).",
        "",
    ]
    (ROOT / "results" / "source_syntax_comparison.md").write_text("\n".join(report))
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
