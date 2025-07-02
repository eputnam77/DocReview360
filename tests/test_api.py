from fastapi.testclient import TestClient

from docuflow.api import app


def test_list_projects() -> None:
    client = TestClient(app)
    resp = client.get("/projects")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Example"


def test_list_documents() -> None:
    client = TestClient(app)
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "1"
