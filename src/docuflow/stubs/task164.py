"""Implementation for task 164."""

from time import perf_counter

from ..stubs import record_task_completion
from ..search import list_projects


def analyze_performance(iterations: int = 100) -> str:
    """Return a short timing summary for ``list_projects`` calls."""

    record_task_completion(164)
    start = perf_counter()
    for _ in range(iterations):
        list_projects()
    duration = perf_counter() - start
    avg = duration / iterations
    return f"avg {avg:.6f}s over {iterations} calls"
