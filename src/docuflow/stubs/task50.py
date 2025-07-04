"""Expose dual status API helpers."""

from ..status import internal_status, public_status
from . import record_task_completion


def task50() -> tuple[dict[str, int], dict[str, int]]:
    """Return public and internal status information."""
    record_task_completion(50)
    return public_status(), internal_status()
