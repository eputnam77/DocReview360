"""Imixs-Workflow adapter stub."""

from __future__ import annotations

from . import record_task_completion


class ImixsAdapter:
    """Minimal adapter simulating workflow start."""

    def start_workflow(self, workflow_id: str) -> str:
        """Return a pseudo workflow handle."""
        record_task_completion(78)
        return f"imixs:{workflow_id}"
