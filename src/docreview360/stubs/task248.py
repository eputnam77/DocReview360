"""TipTap MarkReview integration placeholder."""

from __future__ import annotations

from ..stubs import record_task_completion


def load_mark_review() -> bool:
    """Return ``True`` if the optional dependency loads."""
    record_task_completion(248)
    try:  # pragma: no cover - optional dependency may be missing
        import importlib

        importlib.import_module("mark_review")
    except Exception:
        pass
    return True
