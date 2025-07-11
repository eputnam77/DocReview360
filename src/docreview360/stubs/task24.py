"""Collaborative comments helper for task 24."""

from ..comments import add_comment, list_comments


def task24(doc_id: str, user: str, text: str) -> int:
    """Add a comment and return the thread length."""
    add_comment(doc_id, user, text)
    return len(list_comments(doc_id))
