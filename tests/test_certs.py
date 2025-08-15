import hashlib

import pytest

from docreview360.certs import clear_cache, fetch_certificate, register_pinned_chain


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
