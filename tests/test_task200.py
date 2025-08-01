from pathlib import Path

from docreview360.stubs.task200 import task200


def test_task200_checks_docs() -> None:
    """Verify the README mentions Playwright setup."""

    # Use path relative to project root
    project_root = Path(__file__).parent.parent
    assert task200(project_root / "README.md")
