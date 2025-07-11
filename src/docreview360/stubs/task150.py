"""Implementation for task 150."""

from ..compliance_panel import lint_document


def task150(text: str) -> list[str]:
    """Return linter issues for the given text."""

    return lint_document(text)
