from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.rbac import add_role
from docreview360.search import ProjectModel, add_project


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
    if not auth.USER_REPOSITORY.get_user("alice"):
        auth.USER_REPOSITORY.create_user("alice", "Password!1234", otp_secret="123456")
    rbac.reset_role_assignments(include_defaults=False)
    add_role("alice", "manager")
    token = auth.create_access_token({"sub": "alice"})
    resp = client.get(
        "/dashboard/manager",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "workload" in data and "projects" in data


def test_admin_dashboard_endpoint() -> None:
    client = TestClient(app)
    if not auth.USER_REPOSITORY.get_user("alice"):
        auth.USER_REPOSITORY.create_user("alice", "Password!1234", otp_secret="123456")
    rbac.reset_role_assignments(include_defaults=False)
    add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"})
    resp = client.get(
        "/dashboard/admin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data and "status" in data
