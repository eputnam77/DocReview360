# SPDX-License-Identifier: MIT
"""Celery beat schedule editor (Task 149)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .yaml_loader import load_yaml_file, save_yaml_file

SCHEDULE_FILE = Path("schedules.yaml")


def load_schedules(path: Path = SCHEDULE_FILE) -> dict[str, str]:
    """Return a mapping of task names to cron expressions."""
    return load_yaml_file(path, default={}) or {}


def update_schedule(name: str, cron: str, path: Path = SCHEDULE_FILE) -> None:
    """Update ``name`` with ``cron`` schedule."""
    schedules = load_schedules(path)
    schedules[name] = cron
    save_yaml_file(path, schedules)
