"""Backup and disaster-recovery helper."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..backup_utils import create_backup
from . import record_task_completion


def task54(path: str | Path | None = None) -> None:
    """Create a compressed backup at ``path`` or a temp location."""
    target = Path(path) if path else Path(tempfile.gettempdir()) / "docreview360_backup.gz"
    create_backup(target)
    record_task_completion(54)
    return None
