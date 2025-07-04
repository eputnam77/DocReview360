"""Camunda workflow connector stub."""

from __future__ import annotations

from . import record_task_completion


class CamundaClient:
    """Minimal client simulating process start."""

    def start_process(self, process_id: str) -> str:
        """Return a pseudo process instance identifier."""
        record_task_completion(77)
        return f"started:{process_id}"
