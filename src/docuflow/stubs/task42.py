"""Implementation for task 42."""

from ..markreview import apply_markreview
from . import record_task_completion


def task42() -> str:
    """Return a sample MarkReview diff."""
    diff = apply_markreview("old", "new line")
    record_task_completion(42)
    return diff
