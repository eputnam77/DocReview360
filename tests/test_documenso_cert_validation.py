from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from docreview360 import certs
from docreview360.integrations.signature import documenso


def _make_cert_and_sig(content: bytes):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Test")])
    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    sig = key.sign(content, padding.PKCS1v15(), hashes.SHA256())
    return cert, sig


def test_validate_signature_uses_certificate_status(monkeypatch):
    content = b"doc"
    cert, sig = _make_cert_and_sig(content)
    url = "https://test-cert-documenso"
    documenso.register_test_certificate(url, cert, sig, revoked=None)

    calls = {"n": 0}

    def verifier(c: x509.Certificate, fetcher=None) -> bool:
        calls["n"] += 1
        return True

    monkeypatch.setattr(certs, "verify_certificate_status", verifier)

    assert documenso.validate_signature(content, url, {}) is True
    assert calls["n"] == 1

    def verifier_fail(c: x509.Certificate, fetcher=None) -> bool:
        return False

    monkeypatch.setattr(certs, "verify_certificate_status", verifier_fail)

    assert documenso.validate_signature(content, url, {}) is False

