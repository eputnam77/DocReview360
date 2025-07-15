from docreview360.stubs.task202 import task202


def test_task202_html_snippet() -> None:
    """Docs helper should return simple HTML."""

    assert "<h1>" in task202()
