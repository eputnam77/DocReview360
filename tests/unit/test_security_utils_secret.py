import pytest
from docreview360 import security_utils


def test_create_signature_allows_zero_secret(monkeypatch):
    monkeypatch.setattr(security_utils, "get_secret", lambda name: "0")
    sig = security_utils.create_signature("data")
    # Compute expected value using same algorithm
    import hmac, hashlib
    expected = hmac.new(b"0", b"data", hashlib.sha256).hexdigest()
    assert sig == expected


def test_create_signature_empty_secret_error(monkeypatch):
    with pytest.raises(ValueError):
        security_utils.create_signature("data", secret="")
