from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from docreview360 import email_templates, template_manager
from docreview360.api import app


def _token(client: TestClient, username: str) -> str:
    resp = client.post("/token", data={"username": username, "password": "password"})
    return resp.json()["access_token"]


def test_template_crud_and_download() -> None:
    base = Path(".tmp") / f"template-api-{uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    template_manager.reset_template_store(root=base / "template_store.json")
    client = TestClient(app)
    admin_token = _token(client, "alice")

    resp = client.post(
        "/templates",
        json={
            "name": "policy-doc",
            "content": "<h1>Policy</h1>",
            "docType": "Policy",
            "format": "HTML",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201

    resp = client.get("/templates/policy-doc", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "<h1>Policy</h1>"

    resp = client.get("/templates", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["id"] == "policy-doc" for item in data)

    resp = client.put(
        "/templates/policy-doc",
        json={
            "name": "policy-doc",
            "content": "<h1>Updated</h1>",
            "docType": "Policy",
            "format": "HTML",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    resp = client.get(
        "/templates/policy-doc/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.content == b"<h1>Updated</h1>"

    resp = client.delete(
        "/templates/policy-doc",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


def test_email_template_crud() -> None:
    base = Path(".tmp") / f"email-template-api-{uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    email_templates.reset_email_templates(root=base / "email_templates.json")
    client = TestClient(app)
    admin_token = _token(client, "alice")
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.post(
        "/email-templates",
        json={"name": "welcome", "subject": "Hi", "body": "Hello", "task": "review"},
        headers=headers,
    )
    assert resp.status_code == 201

    resp = client.get("/email-templates/welcome", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["task"] == "review"

    resp = client.get("/email-templates", headers=headers)
    assert resp.status_code == 200
    assert any(item["name"] == "welcome" for item in resp.json())

    resp = client.put(
        "/email-templates/welcome",
        json={"name": "welcome", "subject": "Hello", "body": "Updated", "task": None},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.delete("/email-templates/welcome", headers=headers)
    assert resp.status_code == 204
