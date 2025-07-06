"""Backup and restore Celery tasks (Task 146)."""

from __future__ import annotations

from pathlib import Path

from .backup_utils import create_backup, restore_backup
from .celery_app import app
from .stubs import record_task_completion


@app.task(name="docuflow.create_backup_async")
def create_backup_async(path: str) -> str:
    """Create a backup asynchronously and return the path."""
    target = str(create_backup(Path(path)))
    record_task_completion(146)
    return target


def restore_backup_async(path: str) -> None:
    """Restore a backup and mark task completion."""
    restore_backup(Path(path))
    record_task_completion(146)
