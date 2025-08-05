from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.rbac import add_role, has_role, require_role


def test_admin_access_control() -> None:
    client = TestClient(app)

    # Clear any existing roles for alice to ensure clean state
    from docreview360.rbac import USER_ROLES

    USER_ROLES.clear()  # Clear all roles
    USER_ROLES["alice"] = {"user"}  # Reset to default state

    # token for demo user "alice"
    resp = client.post("/token", data={"username": "alice", "password": "password"})
    token = resp.json()["access_token"]

    # deny access when user lacks role
    r = client.get("/admin/panel", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403

    # grant role and retry
    add_role("alice", "admin")
    r = client.get("/admin/panel", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["admin"] == "ok"


def test_require_role_dependency() -> None:
    add_role("alice", "editor")
    dep = require_role("editor")
    app_local = FastAPI()

    @app_local.get("/edit")
    def edit_route(user: str = Depends(dep)) -> str:  # noqa: F841
        return "ok"

    client = TestClient(app_local)
    token = auth.create_access_token({"sub": "alice"})
    r = client.get("/edit", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert has_role("alice", "editor")
