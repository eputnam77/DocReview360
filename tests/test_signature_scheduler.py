import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

from click.testing import CliRunner
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from docreview360.approvals import ApprovalModel, approvals
from docreview360.audit import clear_audit_log, get_audit_log
from docreview360.cli import cli
from docreview360.documents import import_document
from docreview360.integrations.signature import documenso
from services import signature_verifier


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


def test_verify_document_signatures_logs_result() -> None:
    approvals.clear()
    clear_audit_log()
    doc = import_document("doc.txt", b"hello")
    cert_url = _register_certificate(b"hello")
    appr = ApprovalModel(
        id="a1",
        workflow="wf",
        reviewer="alice",
        document_id=doc.id,
        state="approved",
        signature_provider="documenso",
        signature_id="sig1",
        document_hash=hashlib.sha256(b"hello").hexdigest(),
        certificate_url=cert_url,
        provider_metadata={},
    )
    approvals[appr.id] = appr

    processed = signature_verifier.verify_document_signatures.run()  # type: ignore[attr-defined]
    assert processed == 1
    events = get_audit_log(doc.id)
    assert events[-1].context["signature_valid"] is True


def test_verify_document_signatures_batch_parallel() -> None:
    approvals.clear()
    clear_audit_log()
    doc1 = import_document("d1.txt", b"one")
    doc2 = import_document("d2.txt", b"two")
    cert1 = _register_certificate(b"one")
    cert2 = _register_certificate(b"two")
    approvals["a1"] = ApprovalModel(
        id="a1",
        workflow="wf",
        reviewer="alice",
        document_id=doc1.id,
        state="approved",
        signature_provider="documenso",
        signature_id="s1",
        document_hash=hashlib.sha256(b"one").hexdigest(),
        certificate_url=cert1,
        provider_metadata={},
    )
    approvals["a2"] = ApprovalModel(
        id="a2",
        workflow="wf",
        reviewer="bob",
        document_id=doc2.id,
        state="approved",
        signature_provider="documenso",
        signature_id="s2",
        document_hash=hashlib.sha256(b"two").hexdigest(),
        certificate_url=cert2,
        provider_metadata={},
    )
    processed = signature_verifier.verify_document_signatures.run(  # type: ignore[attr-defined]
        document_ids=[doc1.id, doc2.id], parallel=True
    )
    assert processed == 2
    events1 = get_audit_log(doc1.id)
    events2 = get_audit_log(doc2.id)
    batch1 = events1[-1].context["batch_id"]
    batch2 = events2[-1].context["batch_id"]
    assert batch1 == batch2


def test_cli_verify_signatures() -> None:
    approvals.clear()
    clear_audit_log()
    doc = import_document("doc.txt", b"hello")
    cert_url = _register_certificate(b"hello")
    appr = ApprovalModel(
        id="a1",
        workflow="wf",
        reviewer="alice",
        document_id=doc.id,
        state="approved",
        signature_provider="documenso",
        signature_id="sig1",
        document_hash=hashlib.sha256(b"hello").hexdigest(),
        certificate_url=cert_url,
        provider_metadata={},
    )
    approvals[appr.id] = appr
    runner = CliRunner()
    result = runner.invoke(cli, ["verify-signatures", "--document-id", doc.id])
    assert result.exit_code == 0
    assert "Processed 1 approvals" in result.output
    events = get_audit_log(doc.id)
    assert "batch_id" in events[-1].context


def test_verify_document_signatures_empty_document_ids(monkeypatch) -> None:
    approvals.clear()
    doc = import_document("doc.txt", b"hello")
    approvals["a1"] = ApprovalModel(
        id="a1",
        workflow="wf",
        reviewer="alice",
        document_id=doc.id,
        state="approved",
        signature_provider="stub",
        signature_id="s1",
        document_hash=None,
        certificate_url="cert",
        provider_metadata={},
    )

    class DummyProvider:
        def validate_signature(self, *args, **kwargs):
            return True

    monkeypatch.setattr(signature_verifier, "get_provider", lambda name: DummyProvider())

    processed = signature_verifier.verify_document_signatures.run(document_ids=[])
    assert processed == 0
