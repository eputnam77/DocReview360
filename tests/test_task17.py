from fastapi.testclient import TestClient

from docreview360.api import app


def test_archival_workflow() -> None:
    client = TestClient(app)
    # import a document
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "Archive me", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.post(f"/archive/{doc_id}", json={"metadata": {"note": "v1"}})
    assert resp.status_code == 201
    record = resp.json()
    arch_id = record["id"]
    assert record["document_id"] == doc_id
    assert record["metadata"]["note"] == "v1"
    assert all(key in record for key in ["markdown", "html", "docx", "pdf"])

    resp = client.get(f"/archive/{arch_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == arch_id

    resp = client.get("/archive")
    ids = [r["id"] for r in resp.json()]
    assert arch_id in ids
