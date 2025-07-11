"""Implementation for task 45."""

from ..monitoring import start_observability_stack
from . import record_task_completion


def task45() -> dict[str, str]:
    """Return configuration of the started observability stack."""
    cfg = start_observability_stack(8000, 3000)
    record_task_completion(45)
    return cfg
