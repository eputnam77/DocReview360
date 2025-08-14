from typing import cast

from ..celery_app import fetch_length, word_count
from . import record_task_completion


def task30(value: str = "ok") -> int:
    """Send ``value`` through the Celery ``word_count`` task and return the result."""
    result = word_count.delay(value)
    record_task_completion(30)
    return cast(int, result.get(timeout=10))


def fetch_length_task(url: str) -> int:
    """Return length of ``url`` content via Celery."""
    res = fetch_length.delay(url)
    record_task_completion(30)
    return cast(int, res.get(timeout=10))
