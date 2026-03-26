"""Tests for configurable export filename templates."""

import pytest
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


def test_positional_placeholder_rejected() -> None:
    doc = DocumentModel(id="abc", content="hello")
    with pytest.raises(ValueError):
        export_document(doc, "markdown", name_template="{0}")


def test_template_sanitises_paths() -> None:
    doc = DocumentModel(id="abc", content="hi")
    _, _, name = export_document(doc, "markdown", name_template="../{id}")
    assert name == ".._abc.md"
