import hashlib
import pytest

from docreview360.certs import register_pinned_chain, fetch_certificate, clear_cache


def test_fetch_certificate_case_insensitive():
    clear_cache()
    data = b"demo"
    fingerprint = hashlib.sha256(data).hexdigest().upper()
    register_pinned_chain("EXAMPLE.COM", fingerprint)
    # Should succeed even though host and fingerprint case differ
    assert fetch_certificate("https://example.com/cert.pem", fetcher=lambda url: data) == data
