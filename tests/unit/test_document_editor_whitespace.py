import pytest
from docreview360.documents import DocumentModel, documents, set_document_editor


def test_set_document_editor_rejects_whitespace():
    documents.clear()
    doc = DocumentModel(id="d1", content="hi")
    documents[doc.id] = doc
    with pytest.raises(ValueError):
        set_document_editor(doc.id, "   ")


def test_set_document_editor_trims_input():
    documents.clear()
    doc = DocumentModel(id="d2", content="hi")
    documents[doc.id] = doc
    returned = set_document_editor(doc.id, "  OnlyOffice  ")
    assert returned.editor == "OnlyOffice"
    assert documents[doc.id].editor == "OnlyOffice"
