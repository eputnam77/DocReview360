"""Approval reset confirmation helper."""

from __future__ import annotations

from typing import Callable

from ..stubs import record_task_completion


def task213(confirm: bool, action: Callable[[], None] | None = None) -> bool:
    """Run ``action`` if ``confirm`` is ``True`` and return the result."""

    record_task_completion(213)
    if confirm:
        if action:
            try:
                action()
            except Exception:
                return False
        return True
    return False
