from pathlib import Path

from docreview360.stubs.task200 import task200


def test_task200_checks_docs() -> None:
    """Verify the README mentions Playwright setup."""

    assert task200(Path("README.md"))
