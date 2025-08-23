from docreview360 import documents as documents_module
from docreview360 import logs, search, workflows
from docreview360.stubs.task50 import task50


def test_status_counts() -> None:
    documents_module.documents.clear()
    search.projects.clear()
    workflows.workflows.clear()
    logs.clear_logs()
    public, internal = task50()
    assert public == {"projects": 0, "documents": 0}
    assert "logs" in internal and "workflows" in internal
