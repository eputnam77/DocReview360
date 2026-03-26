# SPDX-License-Identifier: MIT
"""Wrapper regression helpers."""

from __future__ import annotations

from pathlib import Path


def run_regression(fixtures: Path) -> int:
    """Count Markdown files under ``fixtures`` as dummy regression."""
    if not fixtures.exists():
        raise FileNotFoundError(fixtures)
    # ``glob`` only searches the top level; use ``rglob`` so nested fixtures are
    # included.  Tests place Markdown files in sub-directories and expect them
    # to contribute to the regression count.  The previous implementation missed
    # those files which under-reported the number of processed fixtures.
    count = len(list(fixtures.rglob("*.md")))
    return count
