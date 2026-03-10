# SPDX-License-Identifier: MIT
"""Backup and restore Celery tasks (Task 146)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from celery import Task
from celery.schedules import crontab

from .backup_utils import create_backup, restore_backup
from .celery_app import app


def create_backup_async(path: str) -> str:
    """Create a backup asynchronously and return the path."""
    target = str(create_backup(Path(path)))
    return target


create_backup_async = cast(
    Task,
    app.task(name="docreview360.create_backup_async")(create_backup_async),
)


def restore_backup_async(path: str) -> None:
    """Restore a backup and mark task completion."""
    restore_backup(Path(path))


def schedule_daily_backup(path: str) -> None:
    """Configure a daily Celery beat task creating backups."""
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["daily_backup"] = {
        "task": "docreview360.create_backup_async",
        "schedule": crontab(hour=2, minute=0),
        "args": (path,),
    }
