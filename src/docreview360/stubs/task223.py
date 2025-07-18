"""Document converter stub (Task 223)."""

from __future__ import annotations

from pathlib import Path

from ..stubs import record_task_completion


def convert_document(source: Path, output_format: str) -> Path:
    """Convert ``source`` to ``output_format`` and return new path."""
    record_task_completion(223)
    raise NotImplementedError("task 223 not implemented")
