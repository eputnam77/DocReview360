import pytest

from docreview360.documents import DocumentModel
from docreview360.exporter import preview_document


def test_preview_document_length_type_validation():
    doc = DocumentModel(id="x", content="hello")
    with pytest.raises(TypeError, match="length must be an integer"):
        preview_document(doc, "markdown", length=2.5)
