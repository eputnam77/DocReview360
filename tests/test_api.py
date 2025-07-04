from docuflow.api import app
from fastapi.testclient import TestClient


def test_list_projects() -> None:
    client = TestClient(app)
    resp = client.get("/projects")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Example"


def test_list_documents() -> None:
    client = TestClient(app)
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    resp = client.get("/documents")
    assert any(d["id"] == doc_id for d in resp.json())
