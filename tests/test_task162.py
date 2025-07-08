from docuflow.stubs.task162 import render_progress_view


def test_task162_progress_view() -> None:
    """Ensure progress view includes sidebar and banner."""

    html = render_progress_view()
    assert "<aside" in html
    assert "completed" in html
