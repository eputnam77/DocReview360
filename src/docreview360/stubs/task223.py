"""Document converter stub (Task 223)."""

from __future__ import annotations

from pathlib import Path

from ..stubs import record_task_completion


def convert_document(source: Path, output_format: str) -> Path:
    """Convert ``source`` to ``output_format`` and return new path."""
    record_task_completion(223)
    if output_format.lower() not in {"pdf", "html"}:
        raise ValueError("unsupported format")
    return source.with_suffix(f".{output_format}")
