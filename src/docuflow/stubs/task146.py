"""Implementation for task 146."""

from ..backup_panel import create_backup_async


def task146(path: str) -> str:
    """Create a backup asynchronously."""

    return create_backup_async.delay(path).get(timeout=10)
