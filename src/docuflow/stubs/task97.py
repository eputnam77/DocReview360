"""Observability stack configuration helper."""

from __future__ import annotations

from ..monitoring import init_observability
from . import record_task_completion


def enable_observability(service: str) -> dict[str, str]:
    """Initialise metrics and record completion for ``service``."""

    record_task_completion(97)
    config = init_observability()
    config.update({"service": service, "enabled": "true"})
    return config
