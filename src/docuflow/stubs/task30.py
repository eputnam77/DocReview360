from ..celery_app import echo
from . import record_task_completion


def task30(value: str = "ok") -> str:
    """Send ``value`` through the Celery echo task and return the result."""
    result = echo.delay(value)
    record_task_completion(30)
    return result.get(timeout=10)
