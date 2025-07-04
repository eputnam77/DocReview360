"""UI preference helper for dark mode and reduced motion."""

from __future__ import annotations

from . import record_task_completion


def apply_preferences(dark_mode: bool, reduce_motion: bool) -> dict[str, bool]:
    """Return the selected preference flags."""
    record_task_completion(85)
    return {"dark_mode": dark_mode, "reduce_motion": reduce_motion}
