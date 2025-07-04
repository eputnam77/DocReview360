"""Diff utilities using the Pandiff approach.

This module exposes helpers to generate unified diffs and simple
change-bar metadata for pairs of strings.  The functions are small
wrappers around :mod:`difflib` but provide validation and a stable
interface for the rest of the application.
"""

from __future__ import annotations

from difflib import ndiff, unified_diff
from typing import List, Tuple


def compute_diff(old: str, new: str) -> List[str]:
    """Return a unified diff between ``old`` and ``new``.

    Parameters
    ----------
    old: str
        Original text.
    new: str
        Updated text.

    Returns
    -------
    List[str]
        The unified diff lines.

    Raises
    ------
    ValueError
        If either input is not a string.
    """
    if not isinstance(old, str) or not isinstance(new, str):
        raise ValueError("old and new must be strings")
    return list(unified_diff(old.splitlines(), new.splitlines(), lineterm=""))


def change_bars(old: str, new: str) -> List[Tuple[str, str]]:
    """Return change-bar tuples describing modifications.

    Each tuple is ``(action, line)`` where ``action`` is one of ``"added"``,
    ``"removed"`` or ``"unchanged"``.
    """
    if not isinstance(old, str) or not isinstance(new, str):
        raise ValueError("old and new must be strings")

    result: List[Tuple[str, str]] = []
    for line in ndiff(old.splitlines(), new.splitlines()):
        if line.startswith("+ "):
            result.append(("added", line[2:]))
        elif line.startswith("- "):
            result.append(("removed", line[2:]))
        else:
            result.append(("unchanged", line[2:]))
    return result
