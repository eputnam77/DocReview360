"""TipTap indentation controls placeholder."""

from __future__ import annotations

from ..stubs import record_task_completion


def apply_indent(level: int, command: str) -> int:
    """Return new indent level after ``command``."""
    record_task_completion(245)
    if command == "indent":
        return level + 1
    if command == "outdent":
        return max(level - 1, 0)
    raise ValueError("unknown command")
