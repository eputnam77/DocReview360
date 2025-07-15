"""Message template management."""

from __future__ import annotations

from typing import Dict

from ..stubs import record_task_completion


def task211(store: Dict[str, str], name: str, content: str) -> Dict[str, str]:
    """Add or update a template and return the store."""

    record_task_completion(211)
    store[name] = content
    return store
