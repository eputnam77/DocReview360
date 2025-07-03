"""AI assistance helpers for task 23."""

from ..ai_utils import suggest_document_type, validate_content


def task23(text: str) -> tuple[str, bool]:
    """Return suggested document type and validation flag."""
    return suggest_document_type(text), validate_content(text)
