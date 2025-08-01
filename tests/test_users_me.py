from docreview360.api import app
from fastapi.testclient import TestClient


def test_users_me_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/users/me", headers={"X-User": "alice"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
