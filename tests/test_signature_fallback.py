from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.approvals import (
    approvals,
    create_approval,
    send_for_signature,
    verify_document_signature,
)
from docreview360.integrations.signature import base, documenso


class FailingProvider:
    name = "failing"

    def request_signature(self, *args, **kwargs):  # pragma: no cover - stub
        raise NotImplementedError

    def process_webhook(self, data):  # pragma: no cover - stub
        pass

    def verify_signature(self, signature_id, document):  # pragma: no cover - stub
        return False

    def validate_signature(self, document_bytes, certificate_url, metadata):
        return False

    def health_check(self) -> bool:  # pragma: no cover - stub
        return False


def _register_certificate(content: bytes) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Test")])
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
    signature = key.sign(content, padding.PKCS1v15(), hashes.SHA256())
    url = f"https://test-cert-{uuid4().hex}"
    documenso.register_test_certificate(url, cert, signature)
    return url


def _auth_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _setup_document(client: TestClient, content: bytes):
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", content, "text/markdown")},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    appr = create_approval("wf1", "alice", doc_id, document=content, signature_provider="documenso")
    send_for_signature(appr.id, doc_id, "alice")
    return doc_id, appr


@pytest.fixture
def sample_doc() -> bytes:
    return (Path(__file__).with_name("sample_doc.md")).read_bytes()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_documenso_state() -> None:
    documenso._signatures.clear()
    documenso._sig_workflows.clear()
    documenso._sig_certificates.clear()
    documenso._certificates.clear()
    documenso._reset_circuit_breaker_for_tests()


def test_fallback_and_dual_provider(client: TestClient, sample_doc: bytes) -> None:
    approvals.clear()
    base.providers.clear()
    base.register_provider(documenso.DocumensoProvider())
    base.register_provider(FailingProvider())

    doc_id, appr = _setup_document(client, sample_doc)
    cert_url = _register_certificate(sample_doc)
    documenso.process_webhook(
        {"id": appr.signature_id, "status": "signed", "certificate_url": cert_url}
    )

    result = verify_document_signature(doc_id, provider="failing")
    detail = next(d for d in result["details"] if d["approval_id"] == appr.id)
    assert detail["signature_verified"] is True
    assert detail["provider_results"]["failing"] is False
    assert detail["provider_results"]["documenso"] is True

    result2 = verify_document_signature(doc_id, provider=["failing", "documenso"])
    detail2 = next(d for d in result2["details"] if d["approval_id"] == appr.id)
    assert detail2["provider_results"] == {"failing": False, "documenso": True}
    assert detail2["signature_verified"] is True
