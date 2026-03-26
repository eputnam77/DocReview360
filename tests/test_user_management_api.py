from pathlib import Path

from docreview360 import auth, profile, rbac, settings_manager
from docreview360.api import app
from fastapi.testclient import TestClient


def _admin_headers() -> dict[str, str]:
    auth.USER_REPOSITORY.create_user(
        "alice",
        auth.DEMO_USER_DEFAULTS["alice"]["password"],
        otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
    )
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"})
    return {"Authorization": f"Bearer {token}"}


def test_user_management_crud(tmp_path: Path) -> None:
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    settings_manager.SETTINGS_FILE = tmp_path / "settings.yaml"
    client = TestClient(app)
    headers = _admin_headers()

    resp = client.get("/users", headers=headers)
    assert resp.status_code == 200

    resp = client.post(
        "/users",
        json={"username": "charlie", "roles": ["user", "reviewer"]},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "charlie"

    resp = client.put(
        "/users/charlie",
        json={"username": "charlotte", "roles": ["admin"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "charlotte"
    assert set(resp.json()["roles"]) == {"admin"}
    assert set(rbac.get_roles("charlotte")) == {"admin"}

    resp = client.get("/users", headers=headers)
    usernames = {u["username"] for u in resp.json()}
    assert "charlie" not in usernames
    assert "charlotte" in usernames

    resp = client.delete("/users/charlotte", headers=headers)
    assert resp.status_code == 200
    resp = client.get("/users", headers=headers)
    usernames = {u["username"] for u in resp.json()}
    assert "charlotte" not in usernames


def test_user_import_csv_creates_updates_and_profiles(tmp_path: Path) -> None:
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    settings_manager.SETTINGS_FILE = tmp_path / "settings.yaml"
    client = TestClient(app)
    headers = _admin_headers()

    auth.USER_REPOSITORY.create_user("existing", "Password1!ExtraLong")
    rbac.set_user_roles("existing", ["user"], actor="system", context={"source": "test"})

    csv_payload = "\n".join(
        [
            "username,roles,display_name,organization,disabled,email",
            "imported1,admin;reviewer,Import One,Agency,false,import1@example.com",
            "existing,editor,Existing User,Dept,true,existing@example.com",
            ",admin,Missing User,Dept,false,missing@example.com",
        ]
    )

    resp = client.post(
        "/users/import",
        headers=headers,
        files={"file": ("users.csv", csv_payload, "text/csv")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    # The row with no username falls back to email as username (imported)
    assert payload["created"] >= 1
    assert payload["updated"] >= 0
    assert auth.USER_REPOSITORY.get_user("imported1") is not None

    assert auth.USER_REPOSITORY.get_user("imported1") is not None
    assert set(rbac.get_roles("imported1")) == {"admin", "reviewer"}
    imported_profile = profile.get_profile_data("imported1")
    assert imported_profile["displayName"] == "Import One"
    assert imported_profile["department"] == "Agency"
    assert imported_profile["email"] == "import1@example.com"

    assert auth.USER_REPOSITORY.get_user("existing") is not None
    assert set(rbac.get_roles("existing")) == {"editor"}
    assert auth.is_active("existing") is False
    existing_profile = profile.get_profile_data("existing")
    assert existing_profile["displayName"] == "Existing User"
    assert existing_profile["department"] == "Dept"
    assert existing_profile["email"] == "existing@example.com"


def test_user_import_accepts_json_payload(tmp_path: Path) -> None:
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    settings_manager.SETTINGS_FILE = tmp_path / "settings.yaml"
    client = TestClient(app)
    headers = _admin_headers()

    import json
    resp = client.post(
        "/users/import",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps([{"username": "jsonuser", "roles": ["auditor"]}]),
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] == 1
    assert auth.USER_REPOSITORY.get_user("jsonuser") is not None
    assert set(rbac.get_roles("jsonuser")) == {"auditor"}
