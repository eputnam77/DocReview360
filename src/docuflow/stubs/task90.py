"""FedRAMP backup helper stub."""

from __future__ import annotations

from pathlib import Path

from . import record_task_completion


def create_backup(path: str | Path) -> None:
    """Write a dummy encrypted backup file."""
    record_task_completion(90)
    Path(path).write_text("encrypted backup")
