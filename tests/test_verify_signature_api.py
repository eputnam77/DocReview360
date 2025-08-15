from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from docreview360.api import app
from docreview360.approvals import approvals, create_approval, send_for_signature
from docreview360.integrations.signature import documenso


def _register_certificate(
    content: bytes, *, days_valid: int = 1, revoked: bool = False, tamper: bool = False
) -> str:
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
        .not_valid_after(now + timedelta(days=days_valid))
        .sign(key, hashes.SHA256())
    )
    signature = key.sign(content, padding.PKCS1v15(), hashes.SHA256())
    if tamper:
        signature = b"\x00" + signature[1:]
    url = f"test-cert-{uuid4().hex}"
    documenso.register_test_certificate(url, cert, signature, revoked=revoked)
    return url


def _setup_document(client: TestClient) -> tuple[str, object]:
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", b"hello", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    appr = create_approval("wf1", "alice", doc_id, document=b"hello", signature_provider="documenso")
    send_for_signature(appr.id, doc_id, "alice")
    return doc_id, appr


def test_valid_signature() -> None:
    approvals.clear()
    client = TestClient(app)
    doc_id, appr = _setup_document(client)
    cert_url = _register_certificate(b"hello")
    documenso.process_webhook({"id": appr.signature_id, "status": "signed", "certificate_url": cert_url})

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pass"
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert detail["signature_verified"] is True


def test_tampered_signature() -> None:
    approvals.clear()
    client = TestClient(app)
    doc_id, appr = _setup_document(client)
    cert_url = _register_certificate(b"hello", tamper=True)
    try:
        documenso.process_webhook({"id": appr.signature_id, "status": "signed", "certificate_url": cert_url})
    except Exception:
        pass

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert data["status"] == "fail"
    assert detail["certificate_present"] is True
    assert detail["signature_verified"] is False


def test_expired_certificate() -> None:
    approvals.clear()
    client = TestClient(app)
    doc_id, appr = _setup_document(client)
    cert_url = _register_certificate(b"hello", days_valid=-1)
    try:
        documenso.process_webhook({"id": appr.signature_id, "status": "signed", "certificate_url": cert_url})
    except Exception:
        pass

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert data["status"] == "fail"
    assert detail["certificate_present"] is True
    assert detail["signature_verified"] is False


def test_revoked_certificate() -> None:
    approvals.clear()
    client = TestClient(app)
    doc_id, appr = _setup_document(client)
    cert_url = _register_certificate(b"hello", revoked=True)
    try:
        documenso.process_webhook({"id": appr.signature_id, "status": "signed", "certificate_url": cert_url})
    except Exception:
        pass

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert data["status"] == "fail"
    assert detail["certificate_present"] is True
    assert detail["signature_verified"] is False
