from __future__ import annotations

import pytest
from docreview360.security_utils import create_signature, verify_signature


def test_create_signature_requires_secret(monkeypatch) -> None:
    monkeypatch.delenv("DOCREVIEW360_SIGNATURE_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        create_signature("data")

    monkeypatch.setenv("DOCREVIEW360_SIGNATURE_SECRET", "secret")
    sig = create_signature("data")
    assert verify_signature("data", sig)
    with pytest.raises(ValueError):
        create_signature("data", "")
