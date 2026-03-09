from pathlib import Path

from fastapi.testclient import TestClient

from docreview360 import auth, rbac, settings_manager
from docreview360.api import app


def _auth_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"})
    return {"Authorization": f"Bearer {token}"}


def test_role_permissions_endpoint_returns_default_counts(tmp_path: Path) -> None:
    settings_manager.SETTINGS_FILE = tmp_path / "settings.yaml"
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    client = TestClient(app)
    headers = _auth_headers()

    resp = client.get("/rbac/role-permissions", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)

    role_map = {item["role"]: item for item in payload}
    assert "admin" in role_map
    admin = role_map["admin"]
    assert admin["count"] == len(rbac._DEFAULT_ROLE_PERMISSIONS["admin"])
    assert admin["default_count"] == len(rbac._DEFAULT_ROLE_PERMISSIONS["admin"])
    assert set(admin["permissions"]) == set(rbac._DEFAULT_ROLE_PERMISSIONS["admin"])


def test_role_permissions_update_and_reset(tmp_path: Path) -> None:
    settings_manager.SETTINGS_FILE = tmp_path / "settings.yaml"
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    client = TestClient(app)
    headers = _auth_headers()

    update_resp = client.put(
        "/rbac/role-permissions/reviewer",
        headers=headers,
        json={"permissions": ["read", "comment_document"]},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["role"] == "reviewer"
    assert updated["count"] == 2
    assert set(updated["permissions"]) == {"read", "comment_document"}
    assert updated["is_default"] is False

    reset_resp = client.delete("/rbac/role-permissions/reviewer", headers=headers)
    assert reset_resp.status_code == 200
    reset = reset_resp.json()
    assert reset["role"] == "reviewer"
    assert reset["count"] == len(rbac._DEFAULT_ROLE_PERMISSIONS["reviewer"])
    assert set(reset["permissions"]) == set(rbac._DEFAULT_ROLE_PERMISSIONS["reviewer"])
    assert reset["is_default"] is True
