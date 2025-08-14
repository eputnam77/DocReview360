from docreview360 import ai_balancer, auth
from docreview360.ai_writer_assign import assign_technical_writer
from docreview360.api import app
from docreview360.config import Config
from docreview360.rbac import USER_ROLES, add_role
from docreview360.search import ProjectModel, add_project, projects
from fastapi.testclient import TestClient


def test_inactive_users_not_assigned_and_cannot_authenticate() -> None:
    client = TestClient(app)
    snap_projects = {pid: proj.model_copy() for pid, proj in projects.items()}
    snap_roles = USER_ROLES.copy()
    ai_balancer.reset()
    try:
        add_project(ProjectModel(id="p1", name="A"))
        cfg = Config(
            database="sqlite",
            editor="tiptap",
            cms="none",
            auth="oidc",
            ai_auto_assign_writers=True,
        )
        token = client.post(
            "/token", data={"username": "alice", "password": "password"}
        ).json()["access_token"]
        add_role("alice", "admin")
        resp = client.post(
            "/admin/users/bob/status",
            json={"active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"username": "bob", "active": False}
        assert auth.authenticate_user("bob", "password") is None
        chosen = assign_technical_writer("p1", ["alice", "bob"], cfg)
        assert chosen == "alice"
    finally:
        auth.FAKE_USERS_DB["bob"]["active"] = True
        projects.clear()
        projects.update(snap_projects)
        USER_ROLES.clear()
        USER_ROLES.update(snap_roles)
        ai_balancer.reset()
