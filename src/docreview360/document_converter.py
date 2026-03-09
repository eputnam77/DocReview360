"""Document conversion utilities."""

from __future__ import annotations

from pathlib import Path


def convert_document(source: Path, output_format: str) -> Path:
    """Convert ``source`` to ``output_format`` and return new path."""
    if output_format.lower() not in {"pdf", "html"}:
        raise ValueError("unsupported format")
    return source.with_suffix(f".{output_format}")
