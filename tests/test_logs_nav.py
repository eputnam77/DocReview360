from pathlib import Path


def test_sidebar_has_logs_link() -> None:
    sidebar = Path("DocReview360/frontend/components/workflow/Sidebar.tsx").read_text()
    assert "/logs" in sidebar
