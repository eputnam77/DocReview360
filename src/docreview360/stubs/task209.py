"""Document numbering settings."""

from __future__ import annotations

from typing import Optional

from ..stubs import record_task_completion


def task209(manual: bool, number: Optional[str] = None) -> str:
    """Return the next document number."""

    record_task_completion(209)
    if manual and number:
        return number
    return "AUTO-001"
