"""Observability stack configuration stub."""

from __future__ import annotations

from . import record_task_completion


def enable_observability(service: str) -> dict[str, str]:
    """Return stub configuration dict for ``service``."""
    record_task_completion(97)
    return {"service": service, "enabled": "true"}
