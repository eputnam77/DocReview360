"""Project form utilities."""

from __future__ import annotations

from typing import Dict

from ..stubs import record_task_completion


def task207(data: Dict[str, str]) -> bool:
    """Return ``True`` if both phase and workflow are present."""

    record_task_completion(207)
    return "phase" in data and "workflow" in data
