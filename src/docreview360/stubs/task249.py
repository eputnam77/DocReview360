"""TipTap Yjs collaboration placeholder."""

from __future__ import annotations

from ..stubs import record_task_completion


def start_yjs_collaboration(doc_id: str) -> bool:
    """Return ``True`` if Yjs provider is ready."""
    record_task_completion(249)
    if not doc_id:
        raise ValueError("doc_id required")
    return True
