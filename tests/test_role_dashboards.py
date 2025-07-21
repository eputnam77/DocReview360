from docreview360.api import app
from docreview360.search import ProjectModel, add_project
from fastapi.testclient import TestClient


def _setup() -> None:
    add_project(ProjectModel(id="u1", name="UserProj", user="alice"))
    add_project(ProjectModel(id="m1", name="MgrProj", user="bob"))


def test_user_dashboard_endpoint() -> None:
    _setup()
    client = TestClient(app)
    resp = client.get("/dashboard/user", headers={"X-User": "alice"})
    assert resp.status_code == 200
    data = resp.json()
    ids = {e["id"] for e in data}
    assert "u1" in ids


def test_manager_dashboard_endpoint() -> None:
    _setup()
    client = TestClient(app)
    resp = client.get("/dashboard/manager")
    assert resp.status_code == 200
    data = resp.json()
    assert "workload" in data and "projects" in data


def test_admin_dashboard_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/dashboard/admin")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data and "status" in data
