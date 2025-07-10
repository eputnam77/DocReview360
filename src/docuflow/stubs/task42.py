"""Implementation for task 42."""

from ..pandiff import format_change_bars
from . import record_task_completion


def task42() -> str:
    """Return a sample change-bar diff."""
    lines = format_change_bars("old", "new line")
    record_task_completion(42)
    return "\n".join(lines)
