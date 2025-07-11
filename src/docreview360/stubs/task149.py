"""Implementation for task 149."""

from pathlib import Path

from ..schedule_editor import update_schedule


def task149(path: Path | None = None) -> None:
    """Adjust Celery schedule."""

    update_schedule("escalation", "0 3 * * *", path=path or Path("schedules.yaml"))
