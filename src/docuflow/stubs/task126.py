"""Metabase nightly field sync stub implementation."""

from __future__ import annotations

from ..metabase_sync import run_field_sync
from . import record_task_completion


def task126(base_url: str, token: str) -> None:
    """Trigger field sync and log completion."""
    run_field_sync(base_url, token)
    record_task_completion(126)
