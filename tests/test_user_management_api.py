from pathlib import Path

from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app


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
