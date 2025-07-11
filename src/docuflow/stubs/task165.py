"""Implementation for task 165."""

from pathlib import Path

from ..stubs import record_task_completion


def task165() -> bool:
    """Check that the global layout includes the sidebar."""
    record_task_completion(165)
    app_file = Path(__file__).resolve().parents[3] / "frontend/pages/_app.tsx"
    return "<Sidebar" in app_file.read_text()
