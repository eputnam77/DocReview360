from fastapi.testclient import TestClient

from docreview360 import reporting
from docreview360.api import app
from docreview360.approvals import approvals, create_approval
from docreview360.search import ProjectModel, add_project, projects
from docreview360.workflows import create_workflow, workflows


def _cleanup() -> None:
    """Clear global state for clean test runs."""
    projects.clear()
    approvals.clear()
    workflows.clear()


def _setup() -> None:
    _cleanup()  # Ensure clean state
    add_project(ProjectModel(id="pA", name="A", user="alice"))
    add_project(ProjectModel(id="pB", name="B", user="bob"))
    wf_a = create_workflow("pA", ["draft"])
    wf_b = create_workflow("pB", ["draft"])
    create_approval(wf_a.id, "alice", "docA")
    create_approval(wf_b.id, "bob", "docB")


def test_dashboard_filtering_by_user() -> None:
    reporting.reset_metrics_for_testing()
    _setup()
    client = TestClient(app)

    resp = client.get("/reports/dashboard", headers={"X-User": "alice"})
    assert resp.status_code == 200
    ids = [entry["id"] for entry in resp.json()]
    assert ids == ["pA"]

    resp = client.get("/dashboard/widgets", headers={"X-User": "alice"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned"] == 1
    assert data["pending_approvals"] == 1
    assert "avg_quality_score" in data

    resp = client.get("/dashboard/widgets", headers={"X-User": "bob"})
    assert resp.json()["assigned"] == 1
