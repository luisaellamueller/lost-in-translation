"""Check report numbers, paired sample integrity and source-analysis audit trails."""

import json
from pathlib import Path
from statistics import correlation

import pytest

DATA = Path("data/processed")


def read(name):
    return json.loads((DATA / name).read_text())


def test_completed_sample_is_preserved():
    expected = {
        r["document_id"]
        for r in read("complexity_fr_author_translations.json")["records"]
    }
    structure = read("source_structure_comparison.json")
    syntax = read("source_syntax_comparison.json")
    for analysis in structure["analyses"].values():
        records = analysis["records"]
        assert len(records) == len(expected) == 259
        assert {r["document_id"] for r in records} == expected
        for r in records:
            for version in ["source", "official", "generated"]:
                m = r[version]
                assert len(m["sentences"]) == m["sentence_count"]
                assert sum(s["words"] for s in m["sentences"]) == m["word_count"]
    assert {r["document_id"] for r in syntax["records"]} == expected
    assert structure["german_counts_check_against_existing_results"] == []


def test_report_matches_saved_counts_and_correlations():
    structure = read("source_structure_comparison.json")
    for mode, expected in [
        ("punctuation_and_lines", (166, 86)),
        ("punctuation_only", (164, 86)),
    ]:
        records = structure["analyses"][mode]["records"]
        for version, count in zip(["generated", "official"], expected):
            actual = sum(
                r[version]["sentence_count"] == r["source"]["sentence_count"]
                for r in records
            )
            assert actual == count
            assert (
                actual
                == structure["analyses"][mode]["summary"][version][
                    "exact_source_count_matches"
                ]
            )
    syntax = read("source_syntax_comparison.json")
    metric = "mean_sentence_tree_depth"
    source = [r["source"][metric] for r in syntax["records"]]
    for version in ["official", "generated"]:
        target = [r[version][metric] for r in syntax["records"]]
        assert correlation(source, target) == pytest.approx(
            syntax["summary"][metric]["raw"][f"source_{version}_r"]
        )


def test_boundary_rules_and_known_dependency_tree():
    # CI intentionally has no parser packages; run this unit check locally too.
    spacy = pytest.importorskip("spacy")
    pytest.importorskip("wordfreq")
    from spacy.tokens import Doc
    from compare_source_structure import pipeline, measure
    from compare_source_syntax import measure as measure_syntax

    nlp = pipeline("de", ["Art. 3 gilt.\nEin Titel\nDies gilt auch."])
    text = "Art. 3 gilt.\nEin Titel\nDies gilt auch."
    assert measure(nlp, text, True)["sentence_count"] == 3
    assert measure(nlp, text, False)["sentence_count"] == 2
    # Hand-specified dependencies: think -> know -> sing -> birds.
    doc = Doc(
        spacy.blank("en").vocab,
        words=["I", "think", "you", "know", "birds", "sing"],
        heads=[1, 1, 3, 1, 5, 3],
        deps=["nsubj", "ROOT", "nsubj", "ccomp", "nsubj", "ccomp"],
    )
    result = measure_syntax(doc, "en")
    assert result["mean_sentence_tree_depth"] == 3
    assert result["mean_dependency_distance"] == pytest.approx(1.4)
