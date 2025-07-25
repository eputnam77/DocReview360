"""TipTap watermark overlay placeholder."""

from __future__ import annotations

from typing import Any, Dict

from ..stubs import record_task_completion


def apply_watermark(doc: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Return ``doc`` with ``text`` overlay applied."""
    record_task_completion(247)
    raise NotImplementedError
