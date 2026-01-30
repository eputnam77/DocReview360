import pytest

from docreview360 import security_utils


def test_create_signature_allows_zero_secret(monkeypatch):
    monkeypatch.setattr(security_utils, "get_secret", lambda name: "0")
    sig = security_utils.create_signature("data")
    # Compute expected value using same algorithm
    import hashlib
    import hmac

    expected = hmac.new(b"0", b"data", hashlib.sha256).hexdigest()
    assert sig == expected


def test_create_signature_empty_secret_error(monkeypatch):
    with pytest.raises(ValueError):
        security_utils.create_signature("data", secret="")


def test_verify_signature_invalid_secret_returns_false(monkeypatch):
    monkeypatch.setattr(security_utils, "get_secret", lambda name: "s")
    sig = security_utils.create_signature("data")
    assert security_utils.verify_signature("data", sig, secret="") is False


def test_verify_signature_valid(monkeypatch):
    monkeypatch.setattr(security_utils, "get_secret", lambda name: "s")
    sig = security_utils.create_signature("data")
    assert security_utils.verify_signature("data", sig)


def test_verify_signature_missing_secret_returns_false(monkeypatch):
    monkeypatch.setattr(security_utils, "get_secret", lambda name: "")
    assert security_utils.verify_signature("data", "sig") is False


def test_create_signature_missing_secret(monkeypatch):
    monkeypatch.setattr(security_utils, "get_secret", lambda name: "")
    with pytest.raises(RuntimeError):
        security_utils.create_signature("data")


def test_create_signature_custom_secret(monkeypatch):
    sig = security_utils.create_signature("x", secret="y")
    import hashlib
    import hmac

    expected = hmac.new(b"y", b"x", hashlib.sha256).hexdigest()
    assert sig == expected


def test_create_signature_rejects_whitespace():
    with pytest.raises(ValueError):
        security_utils.create_signature("d", secret="   ")


def test_create_signature_strips_custom_secret():
    sig = security_utils.create_signature("x", secret="  y  ")
    import hashlib
    import hmac

    expected = hmac.new(b"y", b"x", hashlib.sha256).hexdigest()
    assert sig == expected
