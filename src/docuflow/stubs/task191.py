"""Implementation for task 191."""

from pathlib import Path

from ..stubs import record_task_completion


def task191() -> bool:
    """Check that the sidebar dashboard link is correct."""
    record_task_completion(191)
    file = Path(__file__).resolve().parents[3] / "frontend/components/workflow/Sidebar.tsx"
    text = file.read_text()
    return '/dashboard"' in text
