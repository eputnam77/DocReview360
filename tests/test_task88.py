from docuflow import documents
from docuflow.stubs.task88 import execute_query


def _seed() -> None:
    """Populate the in-memory store with a minimal record."""
    documents.documents.clear()
    documents.documents["d1"] = documents.DocumentModel(id="d1", content="hi")


def test_execute_query_projects() -> None:
    _seed()
    result = execute_query("{ projects { id name } }")
    assert result["projects"]


def test_execute_query_documents() -> None:
    _seed()
    result = execute_query("{ documents { id content } }")
    assert result["documents"]
