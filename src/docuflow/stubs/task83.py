"""Metabase dashboard integration stub."""

from __future__ import annotations

from typing import List

from . import record_task_completion


class MetabaseClient:
    """Minimal client returning fake chart data."""

    def get_chart(self, chart_id: str) -> dict[str, str]:
        record_task_completion(83)
        return {"id": chart_id, "title": f"Chart {chart_id}"}

    def heatmap(self, project_id: str) -> List[List[int]]:
        """Return dummy heatmap data for ``project_id``."""
        record_task_completion(83)
        return [[i + j for j in range(3)] for i in range(3)]
