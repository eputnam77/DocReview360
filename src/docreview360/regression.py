"""Wrapper regression helpers."""

from __future__ import annotations

from pathlib import Path

from .stubs import record_task_completion


def run_regression(fixtures: Path) -> int:
    """Count Markdown files under ``fixtures`` as dummy regression."""
    if not fixtures.exists():
        raise FileNotFoundError(fixtures)
    count = len(list(fixtures.glob("*.md")))
    record_task_completion(132)
    return count
