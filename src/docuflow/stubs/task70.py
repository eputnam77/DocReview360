"""Synchronise archive folder with SharePoint records."""

from __future__ import annotations

from ..records import sync_to_sharepoint
from . import record_task_completion


def task70(src: str = "archives", dest: str | None = None) -> int:
    """Copy ``src`` to ``dest`` and log completion."""
    copied = sync_to_sharepoint(src, dest)
    record_task_completion(70)
    return copied
