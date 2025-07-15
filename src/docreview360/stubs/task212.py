"""Notification template application."""

from __future__ import annotations

from typing import Dict

from ..stubs import record_task_completion


def task212(template: str, context: Dict[str, str]) -> str:
    """Render ``template`` using ``context`` variables."""

    record_task_completion(212)
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{key}}}", value)
    return result
