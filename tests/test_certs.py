import hashlib
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import ocsp
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID

from docreview360.certs import (
    clear_cache,
    fetch_certificate,
    register_pinned_chain,
    verify_certificate_status,
)


def test_fetch_certificate_caching():
    fingerprint = hashlib.sha256(b"data").hexdigest()
    register_pinned_chain("example.com", fingerprint)
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return b"data"

    assert fetch_certificate("https://example.com/cert", fetcher=fake_fetch) == b"data"
    # second call should use cache
    assert fetch_certificate("https://example.com/cert", fetcher=fake_fetch) == b"data"
    assert calls == ["https://example.com/cert"]
    clear_cache()


def test_fetch_certificate_errors():
    register_pinned_chain("example.com", hashlib.sha256(b"x").hexdigest())
    with pytest.raises(ValueError):
        fetch_certificate("http://example.com/cert", fetcher=lambda u: b"x")
    with pytest.raises(ValueError):
        fetch_certificate("https://unknown.com/cert", fetcher=lambda u: b"x")
    register_pinned_chain("bad.com", hashlib.sha256(b"y").hexdigest())
    with pytest.raises(ValueError):
        fetch_certificate("https://bad.com/cert", fetcher=lambda u: b"x")
    clear_cache()


def test_fetch_certificate_live(monkeypatch):
    class Resp:
        content = b"data"

        def raise_for_status(self):
            pass

    monkeypatch.setattr("httpx.get", lambda url, timeout=5: Resp())
    register_pinned_chain("example.com", hashlib.sha256(b"data").hexdigest())
    assert fetch_certificate("https://example.com/cert") == b"data"
    clear_cache()


def _make_cert(with_crl: bool = False, with_ocsp: bool = False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
    )
    if with_ocsp:
        builder = builder.add_extension(
            x509.AuthorityInformationAccess(
                [
                    x509.AccessDescription(
                        AuthorityInformationAccessOID.OCSP,
                        x509.UniformResourceIdentifier("http://ocsp.test"),
                    )
                ]
            ),
            False,
        )
    if with_crl:
        builder = builder.add_extension(
            x509.CRLDistributionPoints(
                [
                    x509.DistributionPoint(
                        full_name=[x509.UniformResourceIdentifier("http://crl.test")],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]
            ),
            False,
        )
    cert = builder.sign(key, hashes.SHA256())
    return cert, key


def test_verify_certificate_status_ocsp_fetcher():
    cert, key = _make_cert(with_ocsp=True)
    ocsp_resp = (
        ocsp.OCSPResponseBuilder()
        .build_unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED)
        .public_bytes(serialization.Encoding.DER)
    )

    assert verify_certificate_status(cert, issuer=cert, fetcher=lambda u, p: ocsp_resp) is False


def test_verify_certificate_status_ocsp_network(monkeypatch):
    cert, key = _make_cert(with_ocsp=True)
    ocsp_resp = (
        ocsp.OCSPResponseBuilder()
        .build_unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED)
        .public_bytes(serialization.Encoding.DER)
    )

    class Resp:
        content = ocsp_resp

        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "post", lambda *a, **k: Resp())
    assert verify_certificate_status(cert, issuer=cert) is False


def test_verify_certificate_status_crl(monkeypatch):
    cert, key = _make_cert(with_crl=True)
    now = datetime.now(timezone.utc)
    crl = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(cert.issuer)
        .last_update(now)
        .next_update(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.DER)
    )

    def fetch(url, payload):
        return crl

    assert verify_certificate_status(cert, fetcher=fetch) is True
