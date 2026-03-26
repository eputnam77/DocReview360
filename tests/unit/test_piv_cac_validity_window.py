from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from docreview360.piv_cac import validate_piv_certificate


def _build_cert(not_valid_before: datetime, not_valid_after: datetime) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DocReview360")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_validate_piv_certificate_rejects_not_yet_valid() -> None:
    now = datetime.now(timezone.utc)
    pem = _build_cert(now + timedelta(days=1), now + timedelta(days=2))
    assert validate_piv_certificate(pem) is False


def test_validate_piv_certificate_accepts_currently_valid() -> None:
    now = datetime.now(timezone.utc)
    pem = _build_cert(now - timedelta(days=1), now + timedelta(days=1))
    assert validate_piv_certificate(pem) is True
