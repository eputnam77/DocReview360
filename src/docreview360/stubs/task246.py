"""TipTap section node and structure validator placeholder."""

from __future__ import annotations

from typing import List

from ..stubs import record_task_completion


def validate_structure(nodes: List[str]) -> bool:
    """Return ``True`` if ``nodes`` form a valid structure."""
    record_task_completion(246)
    prev_heading = False
    for node in nodes:
        is_heading = node.startswith("h")
        if is_heading and prev_heading:
            return False
        prev_heading = is_heading
    return True
