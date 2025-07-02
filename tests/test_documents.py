from fastapi.testclient import TestClient

from docuflow.api import app


def test_import_and_edit_document() -> None:
    client = TestClient(app)
    content = "# Title\n\nHello"
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", content, "text/markdown")},
    )
    assert resp.status_code == 201
    doc = resp.json()
    doc_id = doc["id"]
    assert doc["content"].startswith("# Title")

    resp = client.get("/documents")
    assert any(d["id"] == doc_id for d in resp.json())

    updated = "# Title\n\nUpdated"
    resp = client.put(
        f"/documents/{doc_id}",
        json={"id": doc_id, "content": updated, "history": []},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == updated
    assert resp.json()["history"] == [content]

    resp = client.get(f"/documents/{doc_id}")
    data = resp.json()
    assert data["content"] == updated
    assert data["history"] == [content]
