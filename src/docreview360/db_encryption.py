# SPDX-License-Identifier: MIT
"""Column-level AES-256-GCM encryption for sensitive SQLAlchemy columns.

Usage::

    from docreview360.db_encryption import EncryptedString, encryption_available

    class MyModel(Base):
        email: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)

The encryption key is read from the ``DOCREVIEW360_COLUMN_ENCRYPTION_KEY``
environment variable (64 hex characters = 32 bytes).

When the env var is not set the type falls back to plain ``String`` behaviour
so that dev environments work without configuration.  Encrypted values are
stored as ``enc:v1:<base64(nonce + ciphertext)>`` to allow transparent future
re-encryption and versioning.

Requires: ``cryptography`` package (already a transitive dep via python-jose).
"""

from __future__ import annotations

import base64
import os
from typing import Any

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

_ENV_KEY = "DOCREVIEW360_COLUMN_ENCRYPTION_KEY"
_PREFIX = "enc:v1:"


def _get_key() -> bytes | None:
    """Return the 32-byte encryption key or None when not configured."""
    raw = os.environ.get(_ENV_KEY, "").strip()
    if not raw:
        return None
    # Accept 64-char hex string (preferred) or raw bytes padded to 32 bytes.
    if len(raw) == 64:
        try:
            return bytes.fromhex(raw)
        except ValueError:
            pass
    return raw.encode()[:32].ljust(32, b"\x00")


def encryption_available() -> bool:
    """Return True when column encryption is configured and the cryptography package is present."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401

        return _get_key() is not None
    except ImportError:
        return False


def _encrypt(value: str, key: bytes) -> str:
    """Encrypt *value* with AES-256-GCM and return a prefixed base64 ciphertext."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, value.encode(), None)
    return _PREFIX + base64.b64encode(nonce + ct).decode()


def _decrypt(value: str, key: bytes) -> str:
    """Decrypt a prefixed AES-256-GCM ciphertext and return the plaintext."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    payload = base64.b64decode(value[len(_PREFIX) :])
    nonce, ct = payload[:12], payload[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()


class EncryptedString(TypeDecorator):  # type: ignore[misc]
    """SQLAlchemy column type that transparently encrypts/decrypts string values.

    Stores data as ``String`` in the database.  Applies AES-256-GCM encryption
    when ``DOCREVIEW360_COLUMN_ENCRYPTION_KEY`` is set; otherwise behaves as a
    plain ``String`` column so dev environments work without configuration.
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 1024, **kw: Any) -> None:
        super().__init__(length, **kw)

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        """Encrypt on the way into the database."""
        if value is None:
            return None
        key = _get_key()
        if key is None or value.startswith(_PREFIX):
            return value
        try:
            return _encrypt(value, key)
        except Exception:
            # Fail open: never lose data due to an encryption error.
            return value

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        """Decrypt on the way out of the database."""
        if value is None:
            return None
        if not value.startswith(_PREFIX):
            return value
        key = _get_key()
        if key is None:
            # Key removed after encryption — return ciphertext rather than crash.
            return value
        try:
            return _decrypt(value, key)
        except Exception:
            return value
