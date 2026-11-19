"""Unit tests of the rules behind the report's numbers (no data needed)."""

import random
from math import comb

import pytest

from author_language_corpus import bio_language, member_language
from special_characters import DASH, fisher_zero_one_sided
from terminology_check import keeps_french_abbreviation, machine_rendering


# --- author language -------------------------------------------------------
def test_bio_language_counts_function_words():
    assert (
        bio_language(
            "Membre du conseil communal de la ville et président de la commission"
        )
        == "FR"
    )
    assert (
        bio_language(
            "Mitglied des Kantonsrats und Präsident der Kommission für Verkehr"
        )
        == "DE"
    )
    assert bio_language("") is None
    assert bio_language("Ingénieur EPFL, MBA") is None  # no function words: undecided


@pytest.mark.parametrize(
    "canton,expected", [("ZH", "DE"), ("GE", "FR"), ("JU", "FR"), ("TI", "IT")]
)
def test_monolingual_canton_decides(canton, expected):
    member = {
        "CantonAbbreviation": canton,
        "Mandates": "Mitglied der Kommission und des Vorstands",
    }
    assert member_language(member) == (expected, "canton")


def test_bilingual_canton_uses_biography():
    fr = {
        "CantonAbbreviation": "VS",
        "Mandates": "Président de la commune et membre du conseil",
    }
    de = {
        "CantonAbbreviation": "VS",
        "AdditionalActivity": "Präsident der Gemeinde und Mitglied des Rats",
    }
    unknown = {"CantonAbbreviation": "BE"}
    assert member_language(fr) == ("FR", "bilingual canton + biography language")
    assert member_language(de) == ("DE", "bilingual canton + biography language")
    assert member_language(unknown) == ("", "unknown")


# --- terminology -----------------------------------------------------------
@pytest.mark.parametrize(
    "term,text,expected",
    [
        ("motion", "Die vorliegende Motion verlangt ...", "kept"),
        ("motion", "Der Motionär verzichtet ...", "kept"),  # derived form counts
        ("motion", "Der vorliegende Antrag zielt darauf ab ...", "Antrag"),
        ("motion", "Mit diesem Entwurf soll ...", "other"),
        ("interpellation", "In seiner Antwort auf meine Anfrage ...", "Anfrage"),
        ("interpellation", "Zahlreiche Politiker haben ...", "lost"),
        ("postulat", "im Antwort auf die Petition von Polla", "Petition"),
        ("Conseil fédéral", "Ich bitte die Bundesregierung ...", "Bundesregierung"),
        ("Conseil fédéral", "Der Bundesrat wird beauftragt ...", "kept"),
    ],
)
def test_machine_rendering(term, text, expected):
    assert machine_rendering(term, text) == expected


def test_french_abbreviation_kept_only_without_german_form():
    assert keeps_french_abbreviation("AVS", "das AVS-Alter")
    assert not keeps_french_abbreviation("AVS", "das AHV-Alter (AVS)")
    assert not keeps_french_abbreviation("AVS", "die Rente")


# --- special characters ----------------------------------------------------
def test_dash_is_spaced_en_dash_not_range():
    assert DASH in "Das ist – wie gesagt – falsch"
    assert DASH not in "in den Jahren 2023–2025"


def test_fisher_matches_hypergeometric_definition():
    # P(no hit in a group of 3 when 2 hits fall among 3 + 5 texts) = C(5,2) / C(8,2)
    assert fisher_zero_one_sided(3, 5, 2) == pytest.approx(comb(5, 2) / comb(8, 2))
    assert fisher_zero_one_sided(0, 10, 3) == 1.0


def test_fisher_by_simulation():
    rng, n_group, n_other, hits = random.Random(1), 40, 120, 6
    texts = list(range(n_group + n_other))
    sims = (
        sum(all(t >= n_group for t in rng.sample(texts, hits)) for _ in range(20000))
        / 20000
    )
    assert sims == pytest.approx(
        fisher_zero_one_sided(n_group, n_other, hits), abs=0.01
    )


def test_convention_rerun_preserves_existing_annotations(tmp_path, monkeypatch):
    import swiss_conventions

    sheet = tmp_path / "terminology_review_french.csv"
    annotation = "document_id,machine_ok\n1,no\n"
    sheet.write_text(annotation, encoding="utf-8")
    monkeypatch.setattr(swiss_conventions, "OUT", tmp_path)
    monkeypatch.setattr(
        swiss_conventions,
        "load",
        lambda: [
            {
                "document_id": 1,
                "year": 2020,
                "input_fr": "Une motion.",
                "reference_de": "Eine Motion.",
                "translation_de": "Ein großer Antrag.",
            }
        ],
    )
    monkeypatch.setattr("sys.argv", ["swiss_conventions.py", "--french"])

    swiss_conventions.main()

    assert sheet.read_text(encoding="utf-8") == annotation
    counts = (tmp_path / "swiss_conventions_counts_french.md").read_text(
        encoding="utf-8"
    )
    assert "| ß (never used in Swiss German) | 0 | 1 |" in counts
