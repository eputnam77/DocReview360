"""Imixs-Workflow adapter stub."""

from __future__ import annotations

import os

import httpx

from . import record_task_completion


class ImixsAdapter:
    """Adapter to start Imixs workflows with an optional HTTP call."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("IMIXS_URL")

    def start_workflow(self, workflow_id: str) -> str:
        """Start a workflow and return its handle."""
        if self.base_url:
            url = f"{self.base_url.rstrip('/')}/workflow/{workflow_id}"
            try:
                resp = httpx.post(url, timeout=5)
                resp.raise_for_status()
                handle = resp.json().get("id", "unknown")
            except httpx.HTTPError as exc:
                raise RuntimeError("Imixs request failed") from exc
            record_task_completion(78)
            return str(handle)
        record_task_completion(78)
        return f"imixs:{workflow_id}"
