import pytest

from docuflow.celery_app import export_documents, reindex_document
from docuflow.documents import DocumentModel, documents
from docuflow.search import search_index


def test_export_documents() -> None:
    doc = DocumentModel(id="1", content="hello", history=[])
    documents["1"] = doc
    result = export_documents(["1"], "markdown")
    assert b"hello" in result


def test_export_documents_invalid() -> None:
    with pytest.raises(ValueError):
        export_documents([], "markdown")


def test_reindex_document() -> None:
    doc = DocumentModel(id="2", content="foo", history=[])
    documents["2"] = doc
    search_index.remove_document("2")
    reindex_document("2")
    assert "2" in {d for ids in search_index.index.values() for d in ids}


def test_reindex_document_empty() -> None:
    with pytest.raises(ValueError):
        reindex_document("")
