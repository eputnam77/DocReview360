import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from docreview360 import auth, doc_types, template_manager
from docreview360.api import app


def _token(client: TestClient, username: str) -> str:
    password = auth.DEMO_USER_DEFAULTS[username]["password"]
    otp_secret = auth.DEMO_USER_DEFAULTS[username].get("otp_secret")
    try:
        auth.USER_REPOSITORY.create_user(username, password, otp_secret=otp_secret)
    except Exception:
        try:
            auth.USER_REPOSITORY.delete_user(username)
            auth.USER_REPOSITORY.create_user(username, password, otp_secret=otp_secret)
        except Exception:
            pass
    resp = client.post("/token", data={"username": username, "password": "password"})
    return resp.json()["access_token"]


def test_template_approval_and_filtering() -> None:
    client = TestClient(app)
    base = Path(".tmp") / f"template-approval-{uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    template_manager.reset_template_store(root=base / "template_store.json")
    doc_types.document_types.clear()

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
