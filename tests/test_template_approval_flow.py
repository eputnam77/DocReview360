import json

from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.template_manager import _template_store


def _token(client: TestClient, username: str) -> str:
    resp = client.post("/token", data={"username": username, "password": "password"})
    return resp.json()["access_token"]


def test_template_approval_and_filtering() -> None:
    client = TestClient(app)
    _template_store.clear()

    admin_token = _token(client, "alice")
    user_token = _token(client, "bob")

    resp = client.post(
        "/templates",
        data={"name": "policy", "meta": json.dumps({})},
        files={"file": ("policy.md", b"# Policy")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201

    resp = client.get("/templates", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.json() == []

    resp = client.post(
        "/templates/policy/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    resp = client.get("/templates", headers={"Authorization": f"Bearer {user_token}"})
    data = resp.json()
    assert len(data) == 1 and data[0]["approved"] is True

    resp = client.post(
        "/templates/policy/retire",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    resp = client.get("/templates", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.json() == []
