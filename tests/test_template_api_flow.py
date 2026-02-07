from fastapi.testclient import TestClient

from docreview360 import email_templates, template_manager
from docreview360.api import app


def _token(client: TestClient, username: str) -> str:
    resp = client.post("/token", data={"username": username, "password": "password"})
    return resp.json()["access_token"]


def test_template_crud_and_download(tmp_path) -> None:
    template_manager.reset_template_store(root=tmp_path / "template_store.json")
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
    )
    assert resp.status_code == 201

    resp = client.get("/templates/policy-doc")
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
    )
    assert resp.status_code == 200

    resp = client.get("/templates/policy-doc/download")
    assert resp.status_code == 200
    assert resp.content == b"<h1>Updated</h1>"

    resp = client.delete("/templates/policy-doc")
    assert resp.status_code == 204


def test_email_template_crud(tmp_path) -> None:
    email_templates.reset_email_templates(root=tmp_path / "email_templates.json")
    client = TestClient(app)

    resp = client.post(
        "/email-templates",
        json={"name": "welcome", "subject": "Hi", "body": "Hello", "task": "review"},
    )
    assert resp.status_code == 201

    resp = client.get("/email-templates/welcome")
    assert resp.status_code == 200
    assert resp.json()["task"] == "review"

    resp = client.get("/email-templates")
    assert resp.status_code == 200
    assert any(item["name"] == "welcome" for item in resp.json())

    resp = client.put(
        "/email-templates/welcome",
        json={"name": "welcome", "subject": "Hello", "body": "Updated", "task": None},
    )
    assert resp.status_code == 200

    resp = client.delete("/email-templates/welcome")
    assert resp.status_code == 204
