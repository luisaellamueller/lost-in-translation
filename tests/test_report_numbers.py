"""Regression tests: rerun the analyses on the committed data and check the numbers in the report."""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from special_characters import fisher_zero_one_sided
from terminology_check import TERMS, machine_rendering

PROC = Path("data/processed")


def translations():
    return json.loads((PROC / "complexity_fr_author_translations.json").read_text(encoding="utf-8"))


def test_translation_sample_size():
    data = translations()
    assert len(data["records"]) == 259 and len(data["failed_records"]) == 1


def test_sample_follows_from_rule_and_seed():
    out = subprocess.run([sys.executable, "scripts/prepare_french_sample.py", "--check"],
                         capture_output=True, text=True, check=True).stdout
    assert "identical to" in out and "True (260 IDs)" in out


@pytest.mark.skipif(not (PROC / "motion_author_language.csv").exists(),
                    reason="run scripts/author_language_corpus.py first")
def test_french_authored_pairs():
    with open(PROC / "motion_author_language.csv", encoding="utf-8") as f:
        lang = {int(r["document_id"]): r["author_language"] for r in csv.DictReader(f)}
    corpus = json.loads((PROC / "motion_corpus.json").read_text(encoding="utf-8"))["records"]
    eligible = [r for r in corpus if r["exclusion_de"] is None and r["exclusion_fr"] is None
                and r["reference_de"] and r["input_fr"]]
    assert len(eligible) == 10573
    assert sum(lang.get(int(r["document_id"])) == "FR" for r in eligible) == 2245


@pytest.mark.parametrize("term,texts,official,machine", [
    ("motion", 43, 41, 22), ("interpellation", 15, 14, 1), ("postulat", 4, 4, 1),
    ("initiative parlementaire", 2, 2, 2), ("Conseil fédéral", 108, 108, 95), ("Conseil des Etats", 3, 3, 2),
])
def test_table1_terminology(term, texts, official, machine):
    fr_pat, de_pat, _, _ = TERMS[term]
    docs = [r for r in translations()["records"] if re.search(fr_pat, r["input_fr"], re.I)]
    assert len(docs) == texts
    assert sum(bool(re.search(de_pat, r["reference_de"])) for r in docs) == official
    assert sum(machine_rendering(term, r["translation_de"]) == "kept" for r in docs) == machine


def test_ss_in_machine_but_not_official():
    recs = translations()["records"]
    assert sum("ß" in r["translation_de"] for r in recs) == 193
    assert sum("ß" in r["reference_de"] for r in recs) == 0


def test_rq1_differences():
    res = json.loads((PROC / "complexity_fr_author_results.json").read_text(encoding="utf-8"))["summary"]
    expected = {"mean_sentence_words": 1.078, "mean_sentence_tree_depth": 0.277,
                "mean_content_word_zipf": 0.118, "lix": 1.774}
    for key, value in expected.items():
        assert res[key]["mean_difference"] == pytest.approx(value, abs=0.001)
        low, high = res[key]["paired_bootstrap_ci95"]
        assert low > 0 and high > 0  # interval excludes zero, as reported


def test_fisher_value_in_report():
    assert fisher_zero_one_sided(435, 1061, 14) == pytest.approx(0.008, abs=0.0005)


def test_screening_annotations_cover_drawn_sample():
    subprocess.run([sys.executable, "scripts/screen_translations.py"], capture_output=True, check=True)
