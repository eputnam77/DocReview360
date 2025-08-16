from docreview360.api import app
from docreview360.logs import clear_logs
from fastapi.testclient import TestClient


def _setup_logs() -> None:
    clear_logs()
    client = TestClient(app)
    client.post("/projects", json={"id": "p1", "name": "Proj", "user": "alice"})
    client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
        data={"project": "p1", "user": "alice"},
    )


def test_export_logs_json() -> None:
    _setup_logs()
    client = TestClient(app)
    headers = {"X-User": "alice"}
    resp = client.get(
        "/logs/export",
        params={"fmt": "json", "action": "create_project"},
        headers=headers,
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["metadata"]["filters"]["action"] == "create_project"
    assert len(data["logs"]) == 1


def test_export_logs_csv() -> None:
    _setup_logs()
    client = TestClient(app)
    headers = {"X-User": "alice"}
    resp = client.get(
        "/logs/export",
        params={"fmt": "csv", "action": "import_document"},
        headers=headers,
    )
    text = resp.text
    assert resp.status_code == 200
    assert text.startswith("# Generated at:")
    assert "# Filters: action=import_document" in text
    assert "import_document" in text.splitlines()[-1]


def test_export_logs_pdf() -> None:
    _setup_logs()
    client = TestClient(app)
    headers = {"X-User": "alice"}
    resp = client.get("/logs/export", params={"fmt": "pdf"}, headers=headers)
    content = resp.content
    assert resp.status_code == 200
    assert content.startswith(b"%PDF-1.4")
    assert b"Generated at:" in content
