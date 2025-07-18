"""UI preference helper for theme and motion settings."""

from __future__ import annotations

from . import record_task_completion


def apply_preferences(theme: str, reduce_motion: bool) -> dict[str, object]:
    """Return the selected preference flags."""
    record_task_completion(85)
    return {"theme": theme, "reduce_motion": reduce_motion}
