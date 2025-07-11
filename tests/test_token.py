from fastapi.testclient import TestClient

from docreview360.api import app


def test_jwt_token_flow() -> None:
    client = TestClient(app)
    resp = client.post("/token", data={"username": "alice", "password": "password"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    protected = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200
    assert protected.json()["username"] == "alice"


def test_login_invalid_credentials() -> None:
    client = TestClient(app)
    resp = client.post("/token", data={"username": "alice", "password": "bad"})
    assert resp.status_code == 401


def test_protected_invalid_token() -> None:
    client = TestClient(app)
    resp = client.get("/me", headers={"Authorization": "Bearer bad"})
    assert resp.status_code == 401


def test_oidc_flow() -> None:
    client = TestClient(app)
    resp = client.post("/oidc/token", data={"username": "alice", "password": "password"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    user_resp = client.get("/oidc/me", headers={"Authorization": f"Bearer {token}"})
    assert user_resp.status_code == 200
    assert user_resp.json()["username"] == "alice"
