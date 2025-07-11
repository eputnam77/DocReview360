"""Performance baseline wrapper for task 131."""

from ..perf import measure_typing_time


def task131() -> float:
    """Return typing baseline duration for 100 characters."""
    return measure_typing_time(100)
