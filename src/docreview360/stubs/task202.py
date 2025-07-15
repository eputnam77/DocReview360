"""In-app documentation page utilities."""

from __future__ import annotations

from ..stubs import record_task_completion


def task202() -> str:
    """Return HTML snippet used for the docs route."""

    record_task_completion(202)
    return "<h1>Documentation</h1>"
