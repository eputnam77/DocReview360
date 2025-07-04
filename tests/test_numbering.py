from docuflow.api import app
from fastapi.testclient import TestClient


def test_project_document_numbering() -> None:
    client = TestClient(app)

    resp = client.post(
        "/projects",
        json={"id": "pnum", "name": "Numbered"},
    )
    assert resp.status_code == 201
    project = resp.json()
    assert isinstance(project["number"], int)

    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
        data={"project": "pnum"},
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert isinstance(doc["number"], int)
