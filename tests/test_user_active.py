from pathlib import Path

import docreview360.ai_writer_assign as writer_assign
import docreview360.rbac as rbac
import pytest
from docreview360 import ai_balancer, auth, search
from docreview360.api import app
from docreview360.config import Config
from docreview360.search import ProjectModel, add_project
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def configure_roles(tmp_path: Path) -> None:
    rbac.configure_role_repository(tmp_path / "roles.db")


def test_inactive_users_not_assigned_and_cannot_authenticate() -> None:
    client = TestClient(app)
    snap_projects = {pid: proj.model_copy() for pid, proj in search.projects.items()}
    ai_balancer.reset()
    try:
        rbac.reset_role_assignments()
        add_project(ProjectModel(id="p1", name="A"))
        writer_assign.projects = search.projects
        cfg = Config(
            database="sqlite",
            editor="tiptap",
            cms="none",
            auth="oidc",
            ai_auto_assign_writers=True,
        )
        token = client.post("/token", data={"username": "alice", "password": "password"}).json()[
            "access_token"
        ]
        rbac.add_role("alice", "admin")
        resp = client.post(
            "/admin/users/bob/status",
            json={"active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"username": "bob", "active": False}
        assert auth.authenticate_user("bob", "password") is None
        chosen = writer_assign.assign_technical_writer("p1", ["alice", "bob"], cfg)
        assert chosen == "alice"
    finally:
        auth.USER_REPOSITORY.set_active("bob", True)
        search.projects.clear()
        search.projects.update(snap_projects)
        writer_assign.projects = search.projects
        rbac.reset_role_assignments()
        ai_balancer.reset()
