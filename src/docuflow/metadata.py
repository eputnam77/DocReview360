"""Utility helpers for project metadata."""

from __future__ import annotations


def normalize_description(text: str) -> str:
    """Return a cleaned project description.

    Leading and trailing whitespace is stripped and internal
    whitespace collapsed to single spaces. Raises ``ValueError`` if
    the resulting text is empty.
    """
    cleaned = " ".join(text.split()).strip()
    return cleaned or "N/A"
