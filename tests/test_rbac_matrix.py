"""RBAC permission tests."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.rbac import ROLE_PERMISSIONS, require_permission, set_user_roles


@pytest.fixture(autouse=True)
def reset_roles(tmp_path) -> None:
    rbac_db_path = tmp_path / "roles.db"
    rbac.configure_role_repository(rbac_db_path)
    rbac.reset_role_assignments()


def test_default_role_permissions_seed() -> None:
    expected = {
        "admin": {
            "create",
            "read",
            "update",
            "delete",
            "edit_field_x",
            "view_audit_log",
            "verification_override",
        },
        "manager": {"create", "read", "update"},
        "sme": {"read", "edit_field_x"},
        "reviewer": {"read"},
        "editor": {"read", "update"},
        "observer": {"read"},
        "user": {"read"},
        "auditor": {"view_audit_log"},
        "verifier": {"verification_override"},
        "qa_role": {"read"},
        "viewer": {"read"},
    }
    assert ROLE_PERMISSIONS == expected
    assert len(ROLE_PERMISSIONS) == 11


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

    rbac.reset_role_assignments(include_defaults=False)
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

    rbac.reset_role_assignments(include_defaults=False)
    set_user_roles("alice", ["observer"])
    r = client.post("/items", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert "created" not in store

    set_user_roles("alice", ["admin"])
    r = client.patch("/items", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert store["patched"] is True
