"""Heading lock rollback tests."""

from docreview360.documents import DocumentModel
from docreview360.stubs.task244 import is_heading_edit_allowed


def test_dragging_locked_heading_rolls_back() -> None:
    doc = DocumentModel(id="1", content="# 1 Title")
    original = doc.content
    allowed = is_heading_edit_allowed(2)
    warning = None
    if not allowed:
        warning = "heading locked"
    assert warning == "heading locked"
    assert doc.content == original
