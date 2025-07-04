"""Simple MarkReview-style track changes helpers."""

from __future__ import annotations

from typing import List

from .pandiff import change_bars


def format_change_bars(old: str, new: str) -> List[str]:
    """Return lines prefixed with markers for additions and removals."""
    bars = change_bars(old, new)
    output = []
    for action, line in bars:
        if action == "added":
            output.append(f"[+] {line}")
        elif action == "removed":
            output.append(f"[-] {line}")
        else:
            output.append(f"    {line}")
    return output
