"""Celery beat schedule editor (Task 149)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .stubs import record_task_completion

SCHEDULE_FILE = Path("schedules.yaml")


def load_schedules(path: Path = SCHEDULE_FILE) -> dict[str, str]:
    """Return a mapping of task names to cron expressions."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def update_schedule(name: str, cron: str, path: Path = SCHEDULE_FILE) -> None:
    """Update ``name`` with ``cron`` schedule."""
    schedules = load_schedules(path)
    schedules[name] = cron
    path.write_text(yaml.safe_dump(schedules))
    record_task_completion(149)
