"""Helpers for polling sign status exactly once."""

from __future__ import annotations

from typing import Callable

from ..stubs import record_task_completion


def task206(check: Callable[[], str]) -> str:
    """Call ``check`` once and return its value."""

    record_task_completion(206)
    return check()
