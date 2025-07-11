from fastapi.testclient import TestClient

from docreview360.api import app


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


def test_metrics_and_audit_endpoints() -> None:
    client = TestClient(app)

    # metrics summary mirrors /reports/summary
    resp1 = client.get("/metrics/summary")
    assert resp1.status_code == 200
    resp2 = client.get("/reports/summary")
    assert resp1.json() == resp2.json()

    # audit endpoint mirrors /logs
    client.get("/projects")  # trigger a log via dependency
    resp3 = client.get("/api/audit")
    resp4 = client.get("/logs")
    assert resp3.status_code == 200
    assert resp3.json() == resp4.json()
