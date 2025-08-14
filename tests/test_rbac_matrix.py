"""RBAC permission tests."""

import importlib.util
import sys
import types
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

# Load auth and rbac modules without executing the heavy package __init__
PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"
pkg = types.ModuleType("docreview360")
pkg.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("docreview360", pkg)

spec_auth = importlib.util.spec_from_file_location("docreview360.auth", PACKAGE_DIR / "auth.py")
auth = importlib.util.module_from_spec(spec_auth)
sys.modules["docreview360.auth"] = auth
spec_auth.loader.exec_module(auth)

spec_rbac = importlib.util.spec_from_file_location("docreview360.rbac", PACKAGE_DIR / "rbac.py")
rbac = importlib.util.module_from_spec(spec_rbac)
sys.modules["docreview360.rbac"] = rbac
spec_rbac.loader.exec_module(rbac)

from docreview360.rbac import (
    ROLE_PERMISSIONS,
    USER_ROLES,
    require_permission,
    set_user_roles,
)


def test_default_role_permissions_seed() -> None:
    expected = {
        "admin": {"create", "read", "update", "delete", "edit_field_x"},
        "manager": {"create", "read", "update"},
        "sme": {"read", "edit_field_x"},
        "reviewer": {"read"},
        "editor": {"read", "update"},
        "observer": {"read"},
        "user": {"read"},
    }
    assert ROLE_PERMISSIONS == expected
    assert len(ROLE_PERMISSIONS) == 7


def test_field_level_rbac() -> None:
    app = FastAPI()
    data: dict[str, int] = {"field_x": 0}

    @app.patch("/resource")
    def patch_resource(
        payload: dict[str, int],
        user: auth.User = Depends(require_permission("edit_field_x")),
    ) -> dict[str, int]:
        data["field_x"] = payload["field_x"]
        return data

    client = TestClient(app)
    token = auth.create_access_token({"sub": "alice"})

    USER_ROLES.clear()
    set_user_roles("alice", ["sme"])
    r = client.patch("/resource", json={"field_x": 1}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert data["field_x"] == 1

    set_user_roles("alice", ["reviewer"])
    r = client.patch("/resource", json={"field_x": 2}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert data["field_x"] == 1


def test_permission_escalation() -> None:
    app = FastAPI()
    store: dict[str, bool] = {}

    @app.post("/items")
    def create_item(
        user: auth.User = Depends(require_permission("create")),
    ) -> dict[str, bool]:
        store["created"] = True
        return {"ok": True}

    @app.patch("/items")
    def patch_item(
        user: auth.User = Depends(require_permission("update")),
    ) -> dict[str, bool]:
        store["patched"] = True
        return {"ok": True}

    client = TestClient(app)
    token = auth.create_access_token({"sub": "alice"})

    USER_ROLES.clear()
    set_user_roles("alice", ["observer"])
    r = client.post("/items", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert "created" not in store

    set_user_roles("alice", ["admin"])
    r = client.patch("/items", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert store["patched"] is True
