"""User theme preference stub (Task 222)."""

from __future__ import annotations

from ..profile import VALID_THEMES, update_preferences
from ..stubs import record_task_completion


def set_user_theme(user_id: str, theme: str) -> None:
    """Persist ``theme`` preference for ``user_id``."""
    if theme not in VALID_THEMES:
        raise ValueError("invalid theme")

    record_task_completion(222)
    update_preferences(user_id, {"theme": theme})
