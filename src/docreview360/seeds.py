"""Utilities for populating sample data during setup."""

from __future__ import annotations

from pathlib import Path

SAMPLE_MD = "# Advisory Circular Sample\n\nThis is a starter document."


def seed_sample_ac(dest_dir: str | Path = "samples") -> Path:
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
    path = Path(dest_dir) / "ac.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SAMPLE_MD)
    return path
