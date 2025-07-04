from ..celery_app import word_count
from . import record_task_completion


def task30(value: str = "ok") -> int:
    """Send ``value`` through the Celery ``word_count`` task and return the result."""
    result = word_count.delay(value)
    record_task_completion(30)
    return result.get(timeout=10)
