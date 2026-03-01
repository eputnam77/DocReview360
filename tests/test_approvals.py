import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.approvals import (
    SignatureValidationError,
    approvals,
    create_approval,
    handle_signature_return,
    refresh_signature_validation_policy,
    send_for_signature,
)
from docreview360.audit import clear_audit_log, get_audit_log
from docreview360.documents import import_document
from docreview360.integrations.signature import documenso
from docreview360.logs import clear_logs, logs


def test_approval_lifecycle() -> None:
    client = TestClient(app)
    # create a workflow first
    wf_resp = client.post(
        "/workflows",
        json={"project": "p1", "phases": ["draft", "review"]},
    )
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    resp = client.post(
        "/approvals",
        json={"workflow": wf_id, "reviewer": "alice", "doc_id": "doc1"},
    )
    assert resp.status_code == 201
    approval = resp.json()
    appr_id = approval["id"]
    assert approval["state"] == "pending"

    resp = client.put(
        f"/approvals/{appr_id}",
        json={"state": "approved", "signature": "signed"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"
    assert resp.json()["signature"] == "signed"

    resp = client.get(f"/approvals/{appr_id}")
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"

    resp = client.get("/approvals", params={"workflow": wf_id})
    assert any(a["id"] == appr_id for a in resp.json())


def test_due_date_updates() -> None:
    client = TestClient(app)
    wf = client.post(
        "/workflows",
        json={"project": "p2", "phases": ["draft"]},
    ).json()
    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = client.post(
        "/approvals",
        json={"workflow": wf["id"], "reviewer": "bob", "due_at": due, "doc_id": "doc2"},
    )
    assert resp.status_code == 201
    appr = resp.json()
    # Normalize both datetime strings to handle different ISO formats
    expected_due = due.replace("+00:00", "Z")
    actual_due = appr["due_at"].replace("+00:00", "Z")
    assert actual_due == expected_due
    new_due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp = client.put(
        f"/approvals/{appr['id']}",
        json={"state": "pending", "due_at": new_due},
    )
    assert resp.status_code == 200
    # Normalize both datetime strings to handle different ISO formats
    expected_new_due = new_due.replace("+00:00", "Z")
    actual_new_due = resp.json()["due_at"].replace("+00:00", "Z")
    assert actual_new_due == expected_new_due


def test_reset_approval() -> None:
    """reset_approval should revert approval state when confirmed."""

    from docreview360 import auth
    from docreview360.approvals import create_approval, reset_approval

    username = f"reset-user-{uuid4().hex[:8]}"
    password = f"Reset!Pass{uuid4().hex[:6]}A1"
    otp = "123456"
    auth.USER_REPOSITORY.create_user(username, password, otp_secret=otp)

    appr = create_approval("wf1", "bob", "doc-reset")
    appr.state = "approved"
    assert reset_approval(
        appr.id,
        True,
        username=username,
        password=password,
        otp=otp,
        reason="test",
    )
    assert appr.state == "pending"

    appr.state = "approved"
    assert not reset_approval(
        appr.id,
        False,
        username=username,
        password=password,
        otp=otp,
        reason="test",
    )
    assert appr.state == "approved"


def test_handle_signature_return_hash_validation() -> None:
    """handle_signature_return should validate document hash."""

    from docreview360.approvals import (
        create_approval,
        handle_signature_return,
        send_for_signature,
    )

    doc = b"hello"
    appr = create_approval("wf42", "carol", "doc42", document=doc, signature_provider="documenso")
    send_for_signature(appr.id, "doc42", "carol")
    assert appr.signature_id is not None
    documenso.complete_signature(appr.signature_id)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test")])
    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    signature = key.sign(doc, padding.PKCS1v15(), hashes.SHA256())
    cert_url = f"https://test-cert-{uuid4().hex}"
    documenso.register_test_certificate(cert_url, cert, signature)
    documenso._sig_certificates[appr.signature_id] = cert_url
    # Valid document should mark approved
    asyncio.run(handle_signature_return(appr.signature_id, document=doc, certificate_url=cert_url))
    assert appr.state == "approved"

    # Mismatch should raise
    appr2 = create_approval(
        "wf43",
        "dave",
        "doc43",
        document=b"orig",
        signature_provider="documenso",
    )
    send_for_signature(appr2.id, "doc43", "dave")
    assert appr2.signature_id is not None
    documenso.complete_signature(appr2.signature_id)
    signature2 = key.sign(b"orig", padding.PKCS1v15(), hashes.SHA256())
    cert_url2 = f"https://test-cert-{uuid4().hex}"
    documenso.register_test_certificate(cert_url2, cert, signature2)
    documenso._sig_certificates[appr2.signature_id] = cert_url2
    with pytest.raises(ValueError):
        asyncio.run(
            handle_signature_return(
                appr2.signature_id, document=b"tampered", certificate_url=cert_url2
            )
        )


def test_signature_invalidated() -> None:
    """handle_signature_return should reject invalid signatures."""

    from docreview360.approvals import (
        create_approval,
        handle_signature_return,
        send_for_signature,
    )

    doc = b"hello"
    appr = create_approval("wf99", "carol", "doc99", document=doc, signature_provider="documenso")
    send_for_signature(appr.id, "doc99", "carol")
    assert appr.signature_id is not None
    # mark as completed but without certificate so verification fails
    documenso.complete_signature(appr.signature_id)
    with pytest.raises(ValueError):
        asyncio.run(handle_signature_return(appr.signature_id, document=doc))


def test_callback_without_certificate_rejected_by_default(monkeypatch) -> None:
    approvals.clear()
    clear_logs()
    clear_audit_log()
    monkeypatch.delenv("DOCREVIEW360_ALLOW_SIGNATURE_FALLBACK", raising=False)
    refresh_signature_validation_policy()

    doc = import_document("doc-no-cert", b"hello")
    appr = create_approval(
        "wf-no-cert",
        "eve",
        doc.id,
        document=b"hello",
        signature_provider="documenso",
    )
    send_for_signature(appr.id, doc.id, "eve")
    documenso.complete_signature(appr.signature_id)

    with pytest.raises(SignatureValidationError) as excinfo:
        asyncio.run(handle_signature_return(appr.signature_id))

    assert excinfo.value.detail["error"] == "missing_certificate"
    assert excinfo.value.detail["approval_id"] == appr.id


def test_callback_without_certificate_allows_flagged_fallback(monkeypatch) -> None:
    approvals.clear()
    clear_logs()
    clear_audit_log()
    monkeypatch.setenv("DOCREVIEW360_ALLOW_SIGNATURE_FALLBACK", "true")
    refresh_signature_validation_policy()

    doc = import_document("doc-fallback", b"hello")
    appr = create_approval(
        "wf-fallback",
        "frank",
        doc.id,
        document=b"hello",
        signature_provider="documenso",
    )
    send_for_signature(appr.id, doc.id, "frank")
    documenso.complete_signature(appr.signature_id)

    asyncio.run(handle_signature_return(appr.signature_id))

    assert appr.state == "approved"
    event = next(e for e in reversed(logs) if e.action == "signature_validation_bypassed")
    assert event.severity == "warning"
    assert event.details["reason"] == "missing_certificate"

    audit_events = get_audit_log(doc.id)
    bypass = [e for e in audit_events if e.event == "signature_validation_bypassed"]
    assert bypass, "expected audit log entry for validation bypass"
    assert bypass[-1].context["fallback_enabled"] is True
    assert bypass[-1].context["reason"] == "missing_certificate"

    monkeypatch.delenv("DOCREVIEW360_ALLOW_SIGNATURE_FALLBACK", raising=False)
    refresh_signature_validation_policy()


def test_send_for_signature_authorization_and_lock() -> None:
    approvals.clear()
    appr = create_approval("wf1", "alice", "doc1", signature_provider="documenso")
    with pytest.raises(PermissionError):
        send_for_signature(appr.id, "doc1", "bob")
    doc_obj = import_document("doc2", b"hi")
    appr2 = create_approval(
        "wf1", "alice", doc_obj.id, delegates=["bob"], signature_provider="documenso"
    )
    send_for_signature(appr2.id, doc_obj.id, "bob")

    doc = b"hello"
    appr3 = create_approval("wf2", "alice", "doc3", document=doc, signature_provider="documenso")
    send_for_signature(appr3.id, "doc3", "alice")
    assert appr3.signature_id is not None
    documenso.complete_signature(appr3.signature_id)
    key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject2 = issuer2 = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test")])
    now2 = datetime.utcnow()
    cert2 = (
        x509.CertificateBuilder()
        .subject_name(subject2)
        .issuer_name(issuer2)
        .public_key(key2.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now2 - timedelta(days=1))
        .not_valid_after(now2 + timedelta(days=1))
        .sign(key2, hashes.SHA256())
    )
    signature2 = key2.sign(doc, padding.PKCS1v15(), hashes.SHA256())
    cert_url3 = f"https://test-cert-{uuid4().hex}"
    documenso.register_test_certificate(cert_url3, cert2, signature2)
    documenso._sig_certificates[appr3.signature_id] = cert_url3
    asyncio.run(
        handle_signature_return(appr3.signature_id, document=doc, certificate_url=cert_url3)
    )
    with pytest.raises(ValueError):
        send_for_signature(appr3.id, "doc3", "alice")


def test_create_approval_freezes_existing_document_hash() -> None:
    approvals.clear()
    doc = import_document("doc-freeze", b"hello")

    approval = create_approval("wf-freeze", "alice", doc.id)

    assert approval.document_hash == hashlib.sha256(doc.content.encode("utf-8")).hexdigest()


def test_send_for_signature_rejects_changed_document_after_hash_freeze() -> None:
    approvals.clear()
    doc = import_document("doc-hash-lock", b"original")
    approval = create_approval("wf-lock", "alice", doc.id)

    # Mutate after approval creation: signing must fail against the frozen hash.
    doc.content = "tampered"

    with pytest.raises(ValueError):
        send_for_signature(approval.id, doc.id, "alice")


def test_send_for_signature_records_signature_content_hash() -> None:
    approvals.clear()
    doc = import_document("doc-signature-record", b"payload")
    approval = create_approval(
        "wf-signature-record",
        "alice",
        doc.id,
        signature_provider="documenso",
    )

    send_for_signature(approval.id, doc.id, "alice")

    assert approval.signature_id is not None
    records = approval.provider_metadata.get("docreview360:signature_records")
    assert isinstance(records, dict)
    assert records[approval.signature_id]["content_hash"] == approval.document_hash

