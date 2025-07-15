from docreview360.stubs.task212 import task212


def test_task212_render_template() -> None:
    """Template should render with context."""

    rendered = task212("Hello {user}", {"user": "Bob"})
    assert rendered == "Hello Bob"
