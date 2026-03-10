# SPDX-License-Identifier: MIT
"""Document comparison utilities."""

from __future__ import annotations

from difflib import SequenceMatcher, unified_diff
from typing import Dict, Tuple


def version_similarity(a: str, b: str) -> float:
    """Return similarity ratio between two document versions."""
    return SequenceMatcher(None, a, b).ratio()


def track_changes(old: str, new: str) -> str:
    """Return a unified diff between ``old`` and ``new`` documents."""
    diff = unified_diff(old.splitlines(), new.splitlines(), lineterm="")
    return "\n".join(diff)


def influence_map(docs: Dict[str, str], threshold: float = 0.5) -> Dict[Tuple[str, str], float]:
    """Return mapping of document pairs with similarity above ``threshold``."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    keys = list(docs)
    mapping: Dict[Tuple[str, str], float] = {}
    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1 :]:
            sim = version_similarity(docs[k1], docs[k2])
            if sim >= threshold:
                mapping[(k1, k2)] = sim
    return mapping
