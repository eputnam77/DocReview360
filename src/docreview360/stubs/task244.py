"""TipTap heading lock placeholder."""

from __future__ import annotations

from ..stubs import record_task_completion


def is_heading_edit_allowed(level: int) -> bool:
    """Return ``False`` if editing heading of ``level`` is disallowed."""
    record_task_completion(244)
    if level < 1:
        raise ValueError("level must be >= 1")
    return level > 2
