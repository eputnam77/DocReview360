from fastapi.testclient import TestClient

from docuflow.api import app
from docuflow.search import ProjectModel, add_project


def test_dashboard_widgets_endpoint() -> None:
    add_project(ProjectModel(id="p1", name="Test"))
    client = TestClient(app)
    resp = client.get("/dashboard/widgets")
    assert resp.status_code == 200
    data = resp.json()
    assert "assigned" in data
    assert "pending_approvals" in data
