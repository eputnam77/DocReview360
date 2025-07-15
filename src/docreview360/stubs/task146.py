"""Implementation for task 146."""

from typing import cast

from ..backup_panel import create_backup_async


def task146(path: str) -> str:
    """Create a backup asynchronously."""

    return cast(str, create_backup_async.delay(path).get(timeout=10))  # type: ignore[attr-defined]
