"""Tests for phase validation using DB-backed phases module."""

import pytest

from docreview360 import phases


@pytest.fixture(autouse=True)
def clean_phases():
    """Reset phases before and after each test."""
    phases.reset_phases()
    yield
    phases.reset_phases()


def test_add_phase_rejects_empty() -> None:
    """add_phase raises ValueError for blank phase names."""
    with pytest.raises(ValueError):
        phases.add_phase(" ")


def test_rename_phase_rejects_empty_new() -> None:
    """rename_phase raises ValueError when new name is empty."""
    phases.add_phase("Alpha")
    with pytest.raises(ValueError):
        phases.rename_phase("Alpha", "")
