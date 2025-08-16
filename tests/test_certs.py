import hashlib
from datetime import datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from docreview360.certs import (
    clear_cache,
    fetch_certificate,
    register_pinned_chain,
    verify_certificate_status,
)


def test_fetch_certificate_caches_and_pins():
    data = b"chain"
    register_pinned_chain("cert", hashlib.sha256(data).hexdigest())
    calls = 0

    def fake_fetch(url: str) -> bytes:
        nonlocal calls
        calls += 1
        return data

    clear_cache()
    out1 = fetch_certificate("https://cert", fetcher=fake_fetch)
    out2 = fetch_certificate("https://cert", fetcher=fake_fetch)
    assert out1 == out2 == data
    assert calls == 1


def test_fetch_certificate_rejects_invalid():
    data = b"chain"
    register_pinned_chain("bad", hashlib.sha256(b"other").hexdigest())

    with pytest.raises(ValueError):
        fetch_certificate("http://bad", fetcher=lambda u: data)
    with pytest.raises(ValueError):
        fetch_certificate("https://bad", fetcher=lambda u: data)


def _make_cert_and_crl(*, revoked: bool = False, next_update: timedelta | None = None):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Test")])
    now = datetime.utcnow()
    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.CRLDistributionPoints(
                [
                    x509.DistributionPoint(
                        full_name=[x509.UniformResourceIdentifier("https://crl.test")],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]
            ),
            critical=False,
        )
    )
    cert = cert_builder.sign(key, hashes.SHA256())
    crl_builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(name)
        .last_update(now - timedelta(minutes=1))
    )
    nu = now + (next_update or timedelta(days=1))
    crl_builder = crl_builder.next_update(nu)
    if revoked:
        revoked_cert = (
            x509.RevokedCertificateBuilder()
            .serial_number(cert.serial_number)
            .revocation_date(now - timedelta(minutes=1))
            .build()
        )
        crl_builder = crl_builder.add_revoked_certificate(revoked_cert)
    crl = crl_builder.sign(private_key=key, algorithm=hashes.SHA256())
    return cert, crl.public_bytes(serialization.Encoding.DER)


def test_verify_certificate_status_caches():
    cert, crl_bytes = _make_cert_and_crl()

    calls = {"n": 0}

    def fetcher(url: str, _: bytes | None) -> bytes:
        calls["n"] += 1
        return crl_bytes

    clear_cache()
    assert verify_certificate_status(cert, fetcher=fetcher) is True
    assert verify_certificate_status(cert, fetcher=fetcher) is True
    assert calls["n"] == 1


def test_verify_certificate_status_revoked():
    cert, crl_bytes = _make_cert_and_crl(revoked=True)

    def fetcher(url: str, _: bytes | None) -> bytes:
        return crl_bytes

    clear_cache()
    assert verify_certificate_status(cert, fetcher=fetcher) is False


def test_verify_certificate_status_stale():
    cert, crl_bytes = _make_cert_and_crl(next_update=timedelta(seconds=-1))

    def fetcher(url: str, _: bytes | None) -> bytes:
        return crl_bytes

    clear_cache()
    assert verify_certificate_status(cert, fetcher=fetcher) is False
