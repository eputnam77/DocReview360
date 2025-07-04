"""Pandiff diff and change-bars helper (task 53)."""

from ..pandiff import compute_diff
from . import record_task_completion


def task53(old: str, new: str) -> list[str]:
    """Return a unified diff between ``old`` and ``new``.

    This function delegates to :func:`docuflow.pandiff.compute_diff` and
    records completion of task 53 for logging purposes.
    """
    diff = compute_diff(old, new)
    record_task_completion(53)
    return diff
