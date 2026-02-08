"""Envelope encryption utilities for encryption at rest."""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .secrets import get_secret
from .settings_manager import load_settings

MAGIC = b"DR360ENC"
VERSION = 1
NONCE_SIZE = 12


class EncryptionError(ValueError):
    """Raised when encryption or decryption fails."""


class EncryptionKeyError(EncryptionError):
    """Raised when key material is missing or invalid."""


@dataclass(frozen=True)
class EncryptionPolicy:
    enabled: bool
    key_id: str | None
    required_for: Tuple[str, ...]

    def requires(self, scope: str) -> bool:
        return self.enabled and scope in self.required_for


def _normalize_required_for(required_for: Any) -> Tuple[str, ...]:
    if not isinstance(required_for, list):
        return ()
    normalized: list[str] = []
    for item in required_for:
        if isinstance(item, str) and item.strip():
            normalized.append(item.strip())
    return tuple(normalized)


def get_encryption_policy(settings: Dict[str, Any] | None = None) -> EncryptionPolicy:
    """Return encryption-at-rest policy derived from settings."""
    if settings is None:
        settings = load_settings()
    security = settings.get("security", {})
    if not isinstance(security, dict):
        security = {}
    enc_cfg = security.get("encryption_at_rest", {})
    if not isinstance(enc_cfg, dict):
        enc_cfg = {}
    enabled = bool(enc_cfg.get("enabled", False))
    key_id = enc_cfg.get("key_id")
    key_id = str(key_id).strip() if isinstance(key_id, str) else None
    required_for = _normalize_required_for(enc_cfg.get("required_for", []))
    return EncryptionPolicy(enabled=enabled, key_id=key_id, required_for=required_for)


def _resolve_key_id(policy: EncryptionPolicy, key_id: str | None) -> str:
    selected = key_id or policy.key_id
    if not selected:
        raise EncryptionKeyError("encryption key id is not configured")
    return selected


def _decode_key_material(secret: str, *, key_id: str) -> bytes:
    if secret.startswith("base64:"):
        payload = secret.removeprefix("base64:")
        try:
            key_bytes = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise EncryptionKeyError(
                f"encryption key material for {key_id} is not valid base64"
            ) from exc
        return key_bytes
    try:
        key_bytes = base64.b64decode(secret, validate=True)
    except (binascii.Error, ValueError):
        key_bytes = secret.encode("utf-8")
    return key_bytes


def _load_key_bytes(key_id: str) -> bytes:
    secret = get_secret(key_id)
    if not secret:
        raise EncryptionKeyError(f"missing encryption key material for {key_id}")
    key_bytes = _decode_key_material(secret, key_id=key_id)
    if len(key_bytes) not in (16, 24, 32):
        raise EncryptionKeyError(
            "encryption key material must be 16, 24, or 32 bytes (raw or base64)"
        )
    return key_bytes


def _build_header(key_id: str, nonce: bytes) -> bytes:
    key_id_bytes = key_id.encode("utf-8")
    if len(key_id_bytes) > 255:
        raise EncryptionKeyError("encryption key id is too long")
    if len(nonce) != NONCE_SIZE:
        raise EncryptionError("invalid nonce length")
    return MAGIC + bytes([VERSION, len(key_id_bytes)]) + key_id_bytes + nonce


def _parse_header(data: bytes) -> tuple[int, str, bytes, bytes]:
    if not data.startswith(MAGIC):
        raise EncryptionError("payload missing encryption header")
    offset = len(MAGIC)
    if len(data) < offset + 2:
        raise EncryptionError("payload header is truncated")
    version = data[offset]
    key_len = data[offset + 1]
    offset += 2
    if version != VERSION:
        raise EncryptionError(f"unsupported encryption version {version}")
    if len(data) < offset + key_len + NONCE_SIZE:
        raise EncryptionError("payload header is truncated")
    key_id = data[offset : offset + key_len].decode("utf-8")
    offset += key_len
    nonce = data[offset : offset + NONCE_SIZE]
    offset += NONCE_SIZE
    ciphertext = data[offset:]
    return version, key_id, nonce, ciphertext


def is_encrypted_payload(data: bytes) -> bool:
    return data.startswith(MAGIC)


def encrypt_payload(
    plaintext: bytes,
    *,
    settings: Dict[str, Any] | None = None,
    key_id: str | None = None,
    associated_data: bytes | None = None,
) -> bytes:
    """Encrypt ``plaintext`` using AES-GCM and return a versioned envelope."""
    policy = get_encryption_policy(settings)
    selected_key = _resolve_key_id(policy, key_id)
    key_bytes = _load_key_bytes(selected_key)
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key_bytes)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    header = _build_header(selected_key, nonce)
    return header + ciphertext


def decrypt_payload(
    payload: bytes,
    *,
    settings: Dict[str, Any] | None = None,
    allow_plaintext: bool = False,
    associated_data: bytes | None = None,
) -> bytes:
    """Decrypt ``payload`` and return plaintext bytes."""
    if not is_encrypted_payload(payload):
        if allow_plaintext:
            return payload
        raise EncryptionError("payload is not encrypted")
    _, key_id, nonce, ciphertext = _parse_header(payload)
    key_bytes = _load_key_bytes(key_id)
    aesgcm = AESGCM(key_bytes)
    try:
        return aesgcm.decrypt(nonce, ciphertext, associated_data)
    except Exception as exc:
        raise EncryptionError("failed to decrypt payload with available key") from exc


def should_encrypt_scope(scope: str, *, settings: Dict[str, Any] | None = None) -> bool:
    """Return ``True`` when encryption is enabled for ``scope``."""
    policy = get_encryption_policy(settings)
    if not policy.enabled:
        return False
    if policy.required_for:
        return scope in policy.required_for
    return True


def enforce_encryption_choice(
    *,
    scope: str,
    encrypt: bool,
    settings: Dict[str, Any] | None = None,
) -> None:
    """Raise when encryption is required but disabled."""
    policy = get_encryption_policy(settings)
    if not encrypt and policy.requires(scope):
        raise EncryptionError(f"encryption is required for {scope}")
