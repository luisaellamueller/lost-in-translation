"""Make the analysis scripts importable and run every test from the repository root."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(autouse=True)
def repo_root(monkeypatch):
    monkeypatch.chdir(ROOT)
    return ROOT
