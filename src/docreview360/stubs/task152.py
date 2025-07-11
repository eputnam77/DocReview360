"""Template migration helper (Task 152)."""

from __future__ import annotations

import difflib

from . import record_task_completion

MAX_DIFF_LINES = 5


def task152(current: str, latest: str) -> str:
    """Return ``latest`` if the diff to ``current`` is small enough."""

    diff = list(difflib.unified_diff(current.splitlines(), latest.splitlines()))
    if len(diff) > MAX_DIFF_LINES:
        raise ValueError("migration too large")

    record_task_completion(152)
    return latest
