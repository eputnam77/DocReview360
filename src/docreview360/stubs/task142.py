"""Implementation for task 142."""

from pathlib import Path

from ..settings_manager import update_setting
from . import record_task_completion


def task142(path: Path | None = None) -> None:
    """Update a sample setting."""

    update_setting("smtp_host", "localhost", path=path or Path("settings.yaml"))
    record_task_completion(142)
    return None
