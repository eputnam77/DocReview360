from types import SimpleNamespace

from cryptography import x509
from cryptography.x509 import ocsp
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

from docreview360 import certs


class _DummyBuilder:
    def add_certificate(self, cert, issuer, algo):
        return self

    def build(self):
        class _Request:
            def public_bytes(self, encoding):
                return b"request"

        return _Request()


class _DummyExtensions:
    def get_extension_for_oid(self, oid):
        if oid == ExtensionOID.AUTHORITY_INFORMATION_ACCESS:
            access = SimpleNamespace(
                access_method=AuthorityInformationAccessOID.OCSP,
                access_location=SimpleNamespace(value="http://ocsp.test"),
            )
            return SimpleNamespace(value=[access])
        raise x509.ExtensionNotFound("missing", oid)


class _DummyCert:
    serial_number = 1001
    extensions = _DummyExtensions()


def test_verify_certificate_status_empty_ocsp_response(monkeypatch):
    class _DummyOcspResponse:
        response_status = ocsp.OCSPResponseStatus.SUCCESSFUL
        responses = []

    monkeypatch.setattr(certs.ocsp, "OCSPRequestBuilder", _DummyBuilder)
    monkeypatch.setattr(certs.ocsp, "load_der_ocsp_response", lambda data: _DummyOcspResponse())

    result = certs.verify_certificate_status(
        _DummyCert(),
        issuer=_DummyCert(),
        fetcher=lambda url, payload: b"ocsp",
    )

    assert result is False
