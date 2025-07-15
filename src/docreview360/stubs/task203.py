"""Integrations page helpers."""

from __future__ import annotations

from typing import Any, Dict

from ..stubs import record_task_completion


def task203(existing: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a configuration dictionary merged with ``existing``."""

    record_task_completion(203)
    base = {"github": True, "slack": False}
    if existing:
        base.update(existing)
    return base
