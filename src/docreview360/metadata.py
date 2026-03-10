# SPDX-License-Identifier: MIT
"""Utility helpers for project metadata."""

from __future__ import annotations


def normalize_description(text: str) -> str:
    """Return a cleaned project description.

    Leading and trailing whitespace is stripped and internal whitespace
    collapsed to single spaces. ``text`` must be a string; passing any
    other type previously raised obscure ``AttributeError`` instances
    when attempting to call ``split``.  We now explicitly validate the
    input and raise ``TypeError`` for non-string values which provides a
    clearer error contract to callers.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        raise ValueError("description cannot be empty")
    return cleaned
