"""Utilities for loading and querying Metabase dashboards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import httpx

from .stubs import record_task_completion


def load_dashboards(path: str | Path) -> Dict[str, Any]:
    """Return the dashboard configuration from ``path``.

    Parameters
    ----------
    path:
        Location of the JSON file describing charts. The file must contain a
        ``{"charts": [...]}" structure.
    """
    src = Path(path)
    try:
        text = src.read_text()
    except OSError as exc:
        raise RuntimeError(f"Failed to read {src}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON dashboard file") from exc
    if not isinstance(data, dict) or "charts" not in data:
        raise ValueError("Dashboard file missing 'charts'")
    return data


class MetabaseClient:
    """Client wrapper returning fake chart data for tests."""

    def __init__(self, dashboards: Dict[str, Any] | None = None) -> None:
        self.dashboards = dashboards or {"charts": []}

    def get_chart(self, chart_id: str) -> Dict[str, str]:
        """Return chart metadata by ``chart_id``."""
        for chart in self.dashboards.get("charts", []):
            if chart.get("id") == chart_id:
                record_task_completion(83)
                return {"id": chart_id, "title": chart.get("title", "")}
        record_task_completion(83)
        return {"id": chart_id, "title": f"Chart {chart_id}"}

    def heatmap(self, project_id: str) -> List[List[int]]:
        """Return a dummy 3x3 heatmap for ``project_id``."""
        record_task_completion(83)
        return [[i + j for j in range(3)] for i in range(3)]


def fetch_dashboards(base_url: str, token: str) -> List[Dict[str, Any]]:
    """Return dashboards from a running Metabase instance."""
    url = f"{base_url.rstrip('/')}/api/dashboard"
    resp = httpx.get(url, headers={"X-Metabase-Session": token}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError("invalid response from Metabase")
    record_task_completion(83)
    return data


def fetch_card_csv(base_url: str, card_id: int, token: str) -> str:
    """Return CSV string for the given card."""
    url = f"{base_url.rstrip('/')}/api/card/{card_id}/query/csv"
    resp = httpx.post(url, headers={"X-Metabase-Session": token}, timeout=10)
    resp.raise_for_status()
    record_task_completion(83)
    return str(resp.text)
