from docuflow.stubs.task161 import render_start_page


def test_task161_start_page() -> None:
    """Ensure the start page renders an upload dropzone."""

    html = render_start_page("demo")
    assert "start-demo" in html
    assert "upload-dropzone" in html
