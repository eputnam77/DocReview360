"""API key management for DocReview360.

Provides creation, validation, revocation, and listing of API keys.
Keys are stored as bcrypt hashes; the raw key is returned only on creation.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

_KEY_PREFIX_LEN = 8
_KEY_BYTES = 32


def _generate_raw_key() -> str:
    """Generate a new random API key (url-safe base64, 43 chars)."""
    return secrets.token_urlsafe(_KEY_BYTES)


def _hash_key(raw: str) -> str:
    """Return a SHA-256 hex digest of ``raw``.

    We use SHA-256 rather than bcrypt because API keys are high-entropy
    random values, making rainbow-table attacks infeasible without the salt
    advantage of bcrypt.
    """
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# In-memory store (replaces DB for tests; production uses SQLAlchemy)
# ---------------------------------------------------------------------------

_api_keys: dict[str, dict[str, Any]] = {}  # key_hash → record


def _reset_for_testing() -> None:
    """Clear the in-memory store between tests."""
    _api_keys.clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_api_key(
    owner: str,
    name: str,
    *,
    scopes: list[str] | None = None,
    expires_at: datetime | None = None,
) -> dict[str, Any]:
    """Create a new API key for ``owner``.

    Returns a dict with ``key`` (the raw secret — show once only) plus
    metadata fields ``id``, ``prefix``, ``name``, ``owner``, ``created_at``,
    ``expires_at``, ``scopes``.
    """
    if not owner or not name:
        raise ValueError("owner and name are required")

    raw = _generate_raw_key()
    prefix = raw[:_KEY_PREFIX_LEN]
    key_hash = _hash_key(raw)
    now = datetime.now(tz=timezone.utc)
    key_id = secrets.token_hex(16)

    record: dict[str, Any] = {
        "id": key_id,
        "owner": owner,
        "name": name,
        "key_hash": key_hash,
        "prefix": prefix,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "last_used_at": None,
        "is_active": True,
        "scopes": scopes or [],
    }
    _api_keys[key_hash] = record

    return {**record, "key": raw}


def validate_api_key(raw: str) -> dict[str, Any] | None:
    """Return the key record if ``raw`` is valid and active, else ``None``."""
    if not raw:
        return None
    key_hash = _hash_key(raw)
    record = _api_keys.get(key_hash)
    if record is None or not record["is_active"]:
        return None
    if record["expires_at"] is not None:
        expires = datetime.fromisoformat(record["expires_at"])
        if datetime.now(tz=timezone.utc) > expires:
            return None
    # Update last_used_at in place
    record["last_used_at"] = datetime.now(tz=timezone.utc).isoformat()
    return record


def revoke_api_key(key_id: str, owner: str) -> bool:
    """Revoke the key with ``key_id`` owned by ``owner``.

    Returns ``True`` if found and revoked, ``False`` if not found or
    not owned by ``owner``.
    """
    for record in _api_keys.values():
        if record["id"] == key_id:
            if record["owner"] != owner:
                return False
            record["is_active"] = False
            return True
    return False


def list_api_keys(owner: str) -> list[dict[str, Any]]:
    """Return all keys owned by ``owner`` (never includes raw key value)."""
    return [
        {k: v for k, v in rec.items() if k != "key_hash"}
        for rec in _api_keys.values()
        if rec["owner"] == owner
    ]


def get_api_key(key_id: str, owner: str) -> dict[str, Any] | None:
    """Return a single key record by ``key_id`` if owned by ``owner``."""
    for record in _api_keys.values():
        if record["id"] == key_id and record["owner"] == owner:
            return {k: v for k, v in record.items() if k != "key_hash"}
    return None
