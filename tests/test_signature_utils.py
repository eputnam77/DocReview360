import os
import pytest

from docreview360.security_utils import create_signature, verify_signature


def test_create_signature_rejects_empty_secret(monkeypatch):
    monkeypatch.setenv("DOCREVIEW360_SIGNATURE_SECRET", "fallback")
    with pytest.raises(ValueError):
        create_signature("data", secret="")


def test_verify_signature_rejects_empty_secret(monkeypatch):
    monkeypatch.setenv("DOCREVIEW360_SIGNATURE_SECRET", "fallback")
    sig = create_signature("data", secret="custom")
    assert verify_signature("data", sig, secret="") is False
