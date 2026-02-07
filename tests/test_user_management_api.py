from pathlib import Path

from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app


def test_user_management_crud(tmp_path: Path) -> None:
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    client = TestClient(app)

    resp = client.get("/users")
    assert resp.status_code == 200

    resp = client.post(
        "/users",
        json={"username": "charlie", "roles": ["user", "reviewer"]},
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "charlie"

    resp = client.put(
        "/users/charlie",
        json={"username": "charlotte", "roles": ["admin"]},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "charlotte"
    assert set(resp.json()["roles"]) == {"admin"}
    assert set(rbac.get_roles("charlotte")) == {"admin"}

    resp = client.get("/users")
    usernames = {u["username"] for u in resp.json()}
    assert "charlie" not in usernames
    assert "charlotte" in usernames

    resp = client.delete("/users/charlotte")
    assert resp.status_code == 200
    resp = client.get("/users")
    usernames = {u["username"] for u in resp.json()}
    assert "charlotte" not in usernames
