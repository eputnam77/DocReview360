"""Celery application and example tasks."""

from __future__ import annotations

import os

from celery import Celery

broker_url = os.environ.get("CELERY_BROKER_URL", "memory://")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://")
app = Celery("docuflow", broker=broker_url, backend=backend_url)
app.conf.task_always_eager = os.environ.get("CELERY_EAGER", "1") == "1"


@app.task(name="docuflow.echo")
def echo(value: str) -> str:
    """Return ``value`` unchanged for testing purposes."""
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    return value
