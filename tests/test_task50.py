from docreview360.documents import documents
from docreview360.search import projects
from docreview360.stubs.task50 import task50


def test_status_counts() -> None:
    documents.clear()
    projects.clear()
    public, internal = task50()
    assert public == {"projects": 0, "documents": 0}
    assert "logs" in internal and "workflows" in internal
