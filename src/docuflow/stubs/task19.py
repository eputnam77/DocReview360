"""Real-time dashboard helpers."""

from ..reporting import dashboard_data


def task19() -> list[dict]:
    """Return dashboard metrics for tests."""
    return [entry.model_dump() for entry in dashboard_data()]
