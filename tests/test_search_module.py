from docreview360 import search
from docreview360.documents import DocumentModel


def setup_function(_):
    search.search_index.projects.clear()
    search.search_index.index.clear()
    search.search_index._next_project_number = 1


def test_search_index_flow():
    proj = search.ProjectModel(id="p1", name="Test", doc_type="Type")
    search.search_index.add_project(proj)
    doc = DocumentModel(id="d1", content="hello world", project="p1")
    search.search_index.add_document(doc)
    assert "hello" in search.search_index.index
    search.search_index.remove_document("d1")
    assert search.search_index.index["hello"] == set()
    assert search.next_project_number() == 2
