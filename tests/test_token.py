from fastapi.testclient import TestClient

from docuflow.api import app


def test_jwt_token_flow() -> None:
    client = TestClient(app)
    resp = client.post("/token", data={"username": "alice", "password": "password"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    protected = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200
    assert protected.json()["username"] == "alice"
