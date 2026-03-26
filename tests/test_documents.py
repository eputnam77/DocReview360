import hashlib
from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.audit import clear_audit_log
from docreview360.documents import (
    DocumentModel,
    autosave_document,
    documents,
    get_document_versions,
    import_document,
)


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for a test 'alice' admin user."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass  # user may already exist
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_import_and_edit_document() -> None:
    clear_audit_log()
    client = TestClient(app)
    headers = _alice_headers()
    content = "# Title\n\nHello"
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", content, "text/markdown")},
        data={"user": "alice"},
        headers=headers,
    )
    assert resp.status_code == 201
    doc = resp.json()
    doc_id = doc["id"]
    assert doc["content"].startswith("# Title")
    expected_hash = hashlib.sha256(content.encode()).hexdigest()
    assert doc["ingestion_hash"] == expected_hash

    resp = client.get("/documents", headers=headers)
    assert any(d["id"] == doc_id for d in resp.json()["items"])

    updated = "# Title\n\nUpdated"
    resp = client.post(
        f"/documents/{doc_id}/revisions",
        json={"content": updated},
        headers={**headers, "X-User": "bob"},
    )
    assert resp.status_code == 201

    resp = client.get(f"/documents/{doc_id}", headers=headers)
    data = resp.json()
    assert data["content"] == updated
    assert [h["content"] for h in data["history"]] == [content, updated]

    resp = client.get(f"/documents/{doc_id}/revisions", headers=headers)
    meta = resp.json()
    assert [m["author"] for m in meta] == ["alice", "bob"]

    resp = client.get(f"/documents/{doc_id}/audit", headers={**headers, "X-User": "alice"})
    events = [e["event"] for e in resp.json()]
    assert events == ["created", "updated"]


def test_autosave_document() -> None:
    doc = import_document("doc.md", b"original")
    autosave_document(doc.id, "original")
    assert get_document_versions(doc.id) == ["original"]
    autosave_document(doc.id, "new")
    assert doc.content == "new"
    assert get_document_versions(doc.id) == ["original", "new"]
    # cleanup to avoid side effects
    from docreview360 import documents as doc_module
    from docreview360 import search as search_module

    search_module.search_index.remove_document(doc.id)
    # Safely remove document if it exists
    if doc.id in doc_module.documents:
        del doc_module.documents[doc.id]


def test_autosave_document_with_empty_history() -> None:
    doc = DocumentModel(id="doc-empty-history", content="draft")
    documents[doc.id] = doc
    saved_doc, revision_id = autosave_document(doc.id, "draft")
    assert saved_doc.history
    assert saved_doc.history[-1].id == revision_id
    assert get_document_versions(doc.id) == ["draft"]
    from docreview360 import fts as fts_module
    from docreview360 import search as search_module

    search_module.search_index.remove_document(doc.id)
    fts_module.remove_document(doc.id)
    documents.pop(doc.id, None)
