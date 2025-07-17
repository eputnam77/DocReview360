from docreview360.doc_types import DocumentTypeModel
from docreview360.search import ProjectModel
from docreview360.stubs.task215 import task215


def test_task215_creates_document() -> None:
    project = ProjectModel(id="p1", name="Test")
    doc_type = DocumentTypeModel(name="AC", template="Hello")
    doc = task215(project, doc_type)
    assert doc.project == "p1" and doc.content == "Hello"
