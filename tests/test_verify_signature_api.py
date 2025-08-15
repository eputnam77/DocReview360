from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.approvals import approvals, create_approval, send_for_signature
from docreview360.integrations.signature import documenso
from docreview360.documents import update_document


def test_verify_signature_endpoint() -> None:
    approvals.clear()
    client = TestClient(app)
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", b"hello", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    appr = create_approval("wf1", "alice", document=b"hello")
    send_for_signature(appr.id, doc_id, "alice")
    documenso.process_webhook(
        {
            "id": appr.signature_id,
            "status": "signed",
            "certificate_url": "cert",
        }
    )

    resp2 = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "pass"
    assert data["details"][0]["approval_id"] == appr.id
    assert data["details"][0]["signature_verified"] is True


def test_verify_signature_mismatched_hash() -> None:
    approvals.clear()
    client = TestClient(app)
    # Import and sign the original document
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", b"hello", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    appr = create_approval("wf1", "alice", document=b"hello")
    send_for_signature(appr.id, doc_id, "alice")
    documenso.process_webhook(
        {"id": appr.signature_id, "status": "signed", "certificate_url": "cert"}
    )

    # Mutate the document after signing so the stored hash mismatches
    update_document(doc_id, "tampered")

    resp2 = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "fail"
    assert data["details"] == []


def test_verify_signature_unsigned() -> None:
    approvals.clear()
    client = TestClient(app)
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", b"hello", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    appr = create_approval("wf1", "alice", document=b"hello")
    send_for_signature(appr.id, doc_id, "alice")

    resp2 = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "fail"
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert detail["hash_valid"] is True
    assert detail["signature_valid"] is False
    assert detail["certificate_present"] is False
    assert detail["signature_verified"] is False


def test_verify_signature_missing_certificate() -> None:
    approvals.clear()
    client = TestClient(app)
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", b"hello", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    appr = create_approval("wf1", "alice", document=b"hello")
    send_for_signature(appr.id, doc_id, "alice")
    documenso.process_webhook(
        {"id": appr.signature_id, "status": "signed"}
    )

    resp2 = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "fail"
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert detail["hash_valid"] is True
    assert detail["signature_valid"] is True
    assert detail["certificate_present"] is False
    assert detail["signature_verified"] is True
