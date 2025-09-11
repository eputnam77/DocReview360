import os
import pytest

from docreview360.security_utils import create_signature


def test_create_signature_whitespace_env_secret(monkeypatch):
    monkeypatch.setenv("DOCREVIEW360_SIGNATURE_SECRET", "   ")
    with pytest.raises(RuntimeError):
        create_signature("payload")
