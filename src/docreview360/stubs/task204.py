"""Phase configuration utilities."""

from __future__ import annotations

from typing import List

from ..stubs import record_task_completion


def task204(phases: List[str], new_phase: str) -> List[str]:
    """Insert ``new_phase`` into ``phases`` if missing and return list."""

    record_task_completion(204)
    if new_phase not in phases:
        phases.append(new_phase)
    return phases
