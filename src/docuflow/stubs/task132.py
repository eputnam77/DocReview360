"""Wrapper regression entry point."""

from pathlib import Path

from ..regression import run_regression


def task132(fixtures: Path | None = None) -> int:
    """Return number of markdown fixtures."""
    path = fixtures or Path("tests/fixtures/editor")
    return run_regression(path)
