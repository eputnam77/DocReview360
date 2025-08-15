from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from docreview360.api import app
from docreview360.approvals import approvals, create_approval, send_for_signature
from docreview360.integrations.signature import documenso
from fastapi.testclient import TestClient


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
    url = f"https://test-cert-{uuid4().hex}"
    documenso.register_test_certificate(url, cert, signature, revoked=revoked)
    return url


@pytest.fixture
def sample_doc() -> bytes:
    return (Path(__file__).with_name("sample_doc.md")).read_bytes()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _setup_document(client: TestClient, content: bytes) -> tuple[str, object]:
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", content, "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    appr = create_approval("wf1", "alice", doc_id, document=content, signature_provider="documenso")
    send_for_signature(appr.id, doc_id, "alice")
    return doc_id, appr


@pytest.fixture
def setup_doc(client: TestClient, sample_doc: bytes) -> tuple[str, object]:
    approvals.clear()
    return _setup_document(client, sample_doc)


def test_valid_signature(client: TestClient, setup_doc: tuple[str, object], sample_doc: bytes) -> None:
    doc_id, appr = setup_doc
    cert_url = _register_certificate(sample_doc)
    documenso.process_webhook(
        {"id": appr.signature_id, "status": "signed", "certificate_url": cert_url}
    )

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pass"
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert detail["signature_verified"] is True


def test_explicit_provider(client: TestClient, setup_doc: tuple[str, object], sample_doc: bytes) -> None:
    doc_id, appr = setup_doc
    cert_url = _register_certificate(sample_doc)
    documenso.process_webhook(
        {"id": appr.signature_id, "status": "signed", "certificate_url": cert_url}
    )

    resp = client.get(f"/documents/{doc_id}/verify-signature", params={"provider": "documenso"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pass"
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert detail["signature_verified"] is True


def test_tampered_signature(client: TestClient, setup_doc: tuple[str, object], sample_doc: bytes) -> None:
    doc_id, appr = setup_doc
    cert_url = _register_certificate(sample_doc, tamper=True)
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


def test_expired_certificate(client: TestClient, setup_doc: tuple[str, object], sample_doc: bytes) -> None:
    doc_id, appr = setup_doc
    cert_url = _register_certificate(sample_doc, days_valid=-1)
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


def test_revoked_certificate(client: TestClient, setup_doc: tuple[str, object], sample_doc: bytes) -> None:
    doc_id, appr = setup_doc
    cert_url = _register_certificate(sample_doc, revoked=True)
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


def test_altered_document(client: TestClient, setup_doc: tuple[str, object], sample_doc: bytes) -> None:
    doc_id, appr = setup_doc
    cert_url = _register_certificate(sample_doc)
    documenso.process_webhook({"id": appr.signature_id, "status": "signed", "certificate_url": cert_url})

    client.put(f"/documents/{doc_id}", json={"id": doc_id, "content": "tampered"})

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert data["status"] == "fail"
    assert detail["hash_valid"] is False


def test_missing_metadata(client: TestClient, setup_doc: tuple[str, object]) -> None:
    doc_id, appr = setup_doc
    try:
        documenso.process_webhook({"id": appr.signature_id, "status": "signed"})
    except Exception:
        pass

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert data["status"] == "fail"
    assert detail["certificate_present"] is False
    assert detail["signature_valid"] is False


def test_non_approved_state(client: TestClient, setup_doc: tuple[str, object]) -> None:
    doc_id, appr = setup_doc
    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert data["status"] == "fail"
    assert detail["signature_valid"] is False


def test_out_of_order_webhook(client: TestClient, setup_doc: tuple[str, object], sample_doc: bytes) -> None:
    doc_id, appr = setup_doc
    cert_url = _register_certificate(sample_doc)
    documenso.process_webhook({"id": appr.signature_id, "status": "signed", "certificate_url": cert_url})
    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pass"

    stale_cert = _register_certificate(sample_doc, tamper=True)
    try:
        documenso.process_webhook(
            {"id": appr.signature_id, "status": "signed", "certificate_url": stale_cert}
        )
    except Exception:
        pass

    resp = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp.status_code == 200
    data = resp.json()
    detail = next(d for d in data["details"] if d["approval_id"] == appr.id)
    assert data["status"] == "fail"
    assert detail["signature_verified"] is False
