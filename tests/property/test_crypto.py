# SPDX-License-Identifier: MIT
"""Property-based tests for crypto/auth utilities (R-15).

Checks invariants for the encrypt/decrypt round-trip and hash functions that
must hold for all valid inputs.
"""

from __future__ import annotations

from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# JWT token invariants
# ---------------------------------------------------------------------------

_username = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=50,
)
_expires_minutes = st.integers(min_value=1, max_value=1440)


@given(username=_username, minutes=_expires_minutes)
@settings(max_examples=100)
def test_jwt_token_is_str(username: str, minutes: int) -> None:
    """create_access_token must return a non-empty string for any username."""
    from docreview360.auth._core import create_access_token

    token = create_access_token({"sub": username}, timedelta(minutes=minutes))
    assert isinstance(token, str)
    assert len(token) > 0


@given(username=_username, minutes=_expires_minutes)
@settings(max_examples=100)
def test_jwt_token_has_three_parts(username: str, minutes: int) -> None:
    """JWT tokens must have exactly three dot-separated parts."""
    from docreview360.auth._core import create_access_token

    token = create_access_token({"sub": username}, timedelta(minutes=minutes))
    parts = token.split(".")
    assert len(parts) == 3, f"Expected 3 JWT parts, got {len(parts)}"


# ---------------------------------------------------------------------------
# Encrypt/decrypt round-trip
# ---------------------------------------------------------------------------

_plaintext = st.binary(min_size=0, max_size=512)

_PROP_KEY_ID = "prop-test-enc-key"


def _enc_settings() -> dict:
    import base64
    import os

    from docreview360.secrets import store_secret

    key = os.urandom(32)
    store_secret(_PROP_KEY_ID, base64.b64encode(key).decode("ascii"))
    return {
        "security": {
            "encryption_at_rest": {
                "enabled": True,
                "key_id": _PROP_KEY_ID,
                "required_for": [],
            }
        }
    }


@given(data=_plaintext)
@settings(max_examples=50)
def test_encrypt_decrypt_roundtrip(data: bytes) -> None:
    """Decrypting an encrypted payload must recover the original bytes."""
    from docreview360.crypto import decrypt_payload, encrypt_payload

    s = _enc_settings()
    ciphertext = encrypt_payload(data, settings=s)
    recovered = decrypt_payload(ciphertext, settings=s)
    assert recovered == data


@given(data=st.binary(min_size=1, max_size=512))
@settings(max_examples=50)
def test_encrypt_output_differs_from_input(data: bytes) -> None:
    """Encrypted output must differ from the plaintext for non-empty data."""
    from docreview360.crypto import encrypt_payload

    s = _enc_settings()
    ciphertext = encrypt_payload(data, settings=s)
    assert ciphertext != data
