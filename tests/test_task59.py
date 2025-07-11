from datetime import datetime, timedelta

import pytest

from docreview360.security_compliance import should_purge, xor_decrypt, xor_encrypt


def test_encrypt_decrypt_roundtrip() -> None:
    data = b"secret"
    key = b"k"
    enc = xor_encrypt(data, key)
    assert xor_decrypt(enc, key) == data


def test_should_purge() -> None:
    old = datetime.utcnow() - timedelta(days=10)
    assert should_purge(old, 5)
    assert not should_purge(datetime.utcnow(), 5)


def test_should_purge_validation() -> None:
    with pytest.raises(ValueError):
        should_purge(datetime.utcnow(), 0)
