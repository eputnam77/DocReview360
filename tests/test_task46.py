from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import docreview360.rbac as rbac
from docreview360 import auth
from docreview360.api import app


def test_admin_access_control() -> None:
    client = TestClient(app)

    # Clear any existing roles for alice to ensure clean state
    rbac.USER_ROLES.clear()
    rbac.USER_ROLES["alice"] = {"user"}

    # token for user "alice"
    resp = client.post("/token", data={"username": "alice", "password": "password"})
    token = resp.json()["access_token"]

    # deny access when user lacks role
    r = client.get("/admin/panel", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403

    # grant role and retry
    rbac.add_role("alice", "admin")
    r = client.get("/admin/panel", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["admin"] == "ok"


def test_require_role_dependency() -> None:
    rbac.add_role("alice", "editor")
    dep = rbac.require_role("editor")
    app_local = FastAPI()

    @app_local.get("/edit")
    def edit_route(user: str = Depends(dep)) -> str:
        return "ok"

    client = TestClient(app_local)
    token = auth.create_access_token({"sub": "alice"})
    r = client.get("/edit", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert rbac.has_role("alice", "editor")
