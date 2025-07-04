"""Celery application and example tasks."""

from __future__ import annotations

import os

import httpx
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


@app.task(name="docuflow.word_count")
def word_count(text: str) -> int:
    """Return the number of words in ``text``."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    return len(text.split())


@app.task(name="docuflow.fetch_length")
def fetch_length(url: str) -> int:
    """Return the length of the response body from ``url``."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must be http or https")
    resp = httpx.get(url, timeout=5)
    resp.raise_for_status()
    return len(resp.text)
