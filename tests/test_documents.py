import hashlib

from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.audit import clear_audit_log
from docreview360.documents import autosave_document, import_document


def test_import_and_edit_document() -> None:
    clear_audit_log()
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
    expected_hash = hashlib.sha256(content.encode()).hexdigest()
    assert doc["ingestion_hash"] == expected_hash

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

    resp = client.get(f"/documents/{doc_id}/audit")
    events = [e["event"] for e in resp.json()]
    assert events == ["created", "updated"]


def test_autosave_document() -> None:
    doc = import_document("doc.md", b"original")
    autosave_document(doc.id, "original")
    assert doc.history == []
    autosave_document(doc.id, "new")
    assert doc.content == "new"
    assert doc.history == ["original"]
    # cleanup to avoid side effects
    from docreview360 import documents as doc_module
    from docreview360 import search as search_module

    search_module.search_index.remove_document(doc.id)
    # Safely remove document if it exists
    if doc.id in doc_module.documents:
        del doc_module.documents[doc.id]
