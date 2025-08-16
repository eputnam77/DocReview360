import os

# Use in-memory database and skip migrations for tests
os.environ.setdefault("DOCREVIEW360_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP", "1")

from docreview360.database import Database

Database._apply_sql_migrations = lambda self, path: None  # type: ignore[misc]

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.approvals import approvals, create_approval
from docreview360.audit import clear_audit_log
from docreview360.documents import import_document


def _auth_headers() -> dict[str, str]:
    token = auth.create_access_token({"sub": "alice"})
    return {"Authorization": f"Bearer {token}"}


def _setup() -> tuple[str, str, str]:
    approvals.clear()
    clear_audit_log()
    doc = import_document("test.txt", b"hello", project="p1", user="alice")
    appr = create_approval("wf1", "alice", doc.id, document=doc.content.encode())
    return doc.id, appr.id, doc.content


def test_approval_history_endpoint() -> None:
    doc_id, approval_id, _ = _setup()
    client = TestClient(app)
    resp = client.get(f"/approvals/{approval_id}/history", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert any(entry["event"] == "approval_created" for entry in data)


def test_signed_document_and_verify_hash() -> None:
    doc_id, approval_id, content = _setup()
    client = TestClient(app)
    resp = client.get(f"/approvals/{approval_id}/signed-document", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.text == content
    resp2 = client.get(f"/approvals/{approval_id}/verify-hash", headers=_auth_headers())
    assert resp2.status_code == 200
    assert resp2.json()["valid"] is True


def test_dashboard_approvals() -> None:
    doc_id, approval_id, _ = _setup()
    client = TestClient(app)
    resp = client.get("/dashboard/approvals", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert any(a["id"] == approval_id for a in data)
