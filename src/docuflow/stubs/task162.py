"""Implementation for task 162."""

from ..stubs import record_task_completion
from ..workflow_components import MOCK_INSTANCE, CompletedBanner, ProgressSidebar


def render_progress_view() -> str:
    """Return HTML for a workflow progress page."""

    record_task_completion(162)
    sidebar = ProgressSidebar().render(MOCK_INSTANCE)
    banner = CompletedBanner().render(MOCK_INSTANCE)
    return f"{sidebar}\n{banner}"
