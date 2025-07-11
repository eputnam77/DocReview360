"""Document numbering helper for task 22."""

from typing import Optional

from ..documents import next_document_number


def task22(project: Optional[str] = None) -> int:
    """Return the next document number for the project."""
    return next_document_number(project)
