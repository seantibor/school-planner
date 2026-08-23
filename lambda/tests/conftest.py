"""Shared pytest fixtures for Lambda tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add lambda/ to sys.path so tests can import modules directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def synthetic_ics() -> str:
    """Load the synthetic 6th grade ICS fixture."""
    return (FIXTURES_DIR / "synthetic_6th_grade.ics").read_text()
