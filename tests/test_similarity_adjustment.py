"""Validate adjusted slopes against a known regression and saved paired data."""

import json
from pathlib import Path

import numpy as np
import pytest

from check_similarity_confounding import coefficient


def test_adjustment_recovers_known_year_effect():
    year = np.arange(12, dtype=float)
    control = year + np.tile([0.0, 2.0, -1.0], 4)
    outcome = 20 + 1.5 * year + 4 * control
    design = np.column_stack([np.ones(12), year, control])
    assert coefficient(design, outcome, np.arange(12)) == pytest.approx(1.5)
    with pytest.raises(ValueError, match="Rank-deficient"):
        coefficient(np.column_stack([design, year]), outcome, np.arange(12))


def test_saved_adjustment_matches_independent_residual_calculation():
    result = json.loads(
        Path("data/processed/similarity_source_adjustment.json").read_text()
    )
    rows = result["records"]
    assert len(rows) == len({r["document_id"] for r in rows}) == 259
    assert len({r["author"] for r in rows}) == result["authors"] == 102
    year = np.array([(r["year"] - 2000) / 10 for r in rows])
    outcome = np.array([r["chrf"] for r in rows])
    controls = np.column_stack(
        [
            np.ones(len(rows)),
            [r["source_mean_sentence_words"] for r in rows],
            [r["source_mean_sentence_tree_depth"] for r in rows],
            np.log([r["source_word_count"] for r in rows]),
        ]
    )
    residual_year = year - controls @ np.linalg.lstsq(controls, year, rcond=None)[0]
    residual_outcome = (
        outcome - controls @ np.linalg.lstsq(controls, outcome, rcond=None)[0]
    )
    slope = residual_year @ residual_outcome / (residual_year @ residual_year)
    assert slope == pytest.approx(result["adjusted"]["slope_per_decade"])
    assert round(slope, 2) == 1.71
    assert round(result["unadjusted"]["slope_per_decade"], 2) == 1.63
