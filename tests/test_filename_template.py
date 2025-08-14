"""Tests for configurable export filename templates."""

from docreview360.documents import DocumentModel
from docreview360.exporter import export_document


def test_default_filename_uses_id() -> None:
    doc = DocumentModel(id="abc", content="hello")
    _, _, name = export_document(doc, "markdown")
    assert name == "abc.md"


def test_custom_filename_template_uses_number() -> None:
    doc = DocumentModel(id="abc", content="hello", number=7)
    _, _, name = export_document(doc, "markdown", name_template="doc-{number}")
    assert name == "doc-7.md"
