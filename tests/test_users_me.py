from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


def test_users_me_endpoint() -> None:
    client = TestClient(app)
    token = auth.create_access_token({"sub": "alice"})
    client.cookies.set("access_token", token)
    resp = client.get("/users/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
