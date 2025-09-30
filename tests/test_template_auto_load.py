"""Auto-load latest template when creating project."""

from docreview360.template_manager import upload_template
from docreview360.doc_types import DocumentTypeModel
from docreview360.search import ProjectModel
from docreview360.stubs.task214 import task214
from docreview360.stubs.task215 import task215


def test_project_creation_autoloads_latest_template() -> None:
    upload_template("ac", b"# AC v1", {"v": 1})
    upload_template("ac", b"# AC v2", {"v": 2})
    doc_type = DocumentTypeModel(
        name="AC", template="", workflow=["Phase"], default_template_id=None
    )
    task214(doc_type, "ac")
    project = ProjectModel(id="p1", name="Proj", user="alice")
    doc = task215(project, doc_type)
    assert doc.content == "# AC v2"
