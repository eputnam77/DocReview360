# SPDX-License-Identifier: MIT
"""Utilities for populating sample data during setup."""

from __future__ import annotations

import os
from pathlib import Path

SAMPLE_MD = "# Advisory Circular Sample\n\nThis is a starter document."


def seed_sample_ac(dest_dir: str | Path | None = None) -> Path:
    """Create a sample AC Markdown file under ``dest_dir``.

    Parameters
    ----------
    dest_dir:
        Target directory for the sample file. It will be created if missing.

    Returns
    -------
    Path
        The path to the created sample file.
    """
    if dest_dir is None:
        dest_dir = os.getenv("DOCREVIEW360_SAMPLE_DIR", "samples")
    path = Path(dest_dir) / "ac.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SAMPLE_MD)
    return path
