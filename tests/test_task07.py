from fastapi.testclient import TestClient

from docreview360.api import app


def test_oidc_token_flow() -> None:
    client = TestClient(app)
    resp = client.post("/oidc/token", data={"username": "alice", "password": "password"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    protected = client.get("/oidc/me", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200
    assert protected.json()["username"] == "alice"
