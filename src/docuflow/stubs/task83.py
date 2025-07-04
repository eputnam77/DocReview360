"""Metabase dashboard integration stub."""

from __future__ import annotations

from . import record_task_completion


class MetabaseClient:
    """Minimal client returning fake chart data."""

    def get_chart(self, chart_id: str) -> dict[str, str]:
        record_task_completion(83)
        return {"id": chart_id, "title": f"Chart {chart_id}"}
