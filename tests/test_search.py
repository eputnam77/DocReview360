from fastapi.testclient import TestClient

from docuflow.api import app


def test_search_returns_matching_document() -> None:
    client = TestClient(app)
    content = "This document contains special keywords"
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", content, "text/markdown")},
        data={"project": "p1", "user": "alice", "priority": 1},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get("/search", params={"q": "special"})
    assert resp.status_code == 200
    assert any(d["id"] == doc_id for d in resp.json())

    resp = client.get("/search", params={"q": "special", "project": "p1"})
    assert len(resp.json()) == 1
