from docreview360.stubs.task199 import task199


def test_task199_returns_version() -> None:
    """The helper should return Playwright version string."""

    version = task199()
    assert isinstance(version, str)
