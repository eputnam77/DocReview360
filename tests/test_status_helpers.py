from docuflow import status
from docuflow.documents import documents, import_document
from docuflow.logs import log_event, logs
from docuflow.search import ProjectModel, add_project, projects
from docuflow.workflows import create_workflow, workflows


def test_status_counts() -> None:
    documents.clear()
    projects.clear()
    workflows.clear()
    logs.clear()

    add_project(ProjectModel(id="s1", name="Status"))
    import_document("d.txt", b"hi", project="s1")
    create_workflow("s1", ["a"])
    log_event("ev")

    assert status.public_status() == {"projects": 1, "documents": 1}
    internal = status.internal_status()
    assert internal["workflows"] == 1
    assert internal["logs"] == 1
