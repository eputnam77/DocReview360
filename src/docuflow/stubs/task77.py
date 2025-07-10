"""Camunda workflow connector stub."""

from __future__ import annotations

import os

import httpx

from . import record_task_completion


class CamundaClient:
    """Client to start Camunda processes or fall back to a stub."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("CAMUNDA_URL")

    def start_process(self, process_id: str) -> str:
        """Start a workflow and return its identifier."""
        if self.base_url:
            url = f"{self.base_url.rstrip('/')}/process-definition/key/{process_id}/start"
            try:
                resp = httpx.post(url, timeout=5)
                resp.raise_for_status()
                pid = resp.json().get("id", "unknown")
            except httpx.HTTPError as exc:  # pragma: no cover - network errors
                raise RuntimeError("Camunda request failed") from exc
            record_task_completion(77)
            return str(pid)
        record_task_completion(77)
        return f"started:{process_id}"
