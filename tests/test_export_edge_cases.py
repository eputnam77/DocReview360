import pytest
from docreview360.documents import DocumentModel
from docreview360.exporter import export_document, preview_document


def test_filename_template_zero_number() -> None:
    doc = DocumentModel(id="1", content="x", number=0)
    _, _, name = export_document(doc, "markdown", name_template="doc-{number}")
    assert name.endswith("doc-0.md")


def test_preview_negative_length_raises() -> None:
    doc = DocumentModel(id="1", content="hello")
    with pytest.raises(ValueError):
        preview_document(doc, "markdown", length=-1)
