# SPDX-License-Identifier: MIT
"""WebAuthn / FIDO2 authentication support."""

from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_logger = logging.getLogger("docreview360.webauthn")

_TRUE_VALUES = {"1", "true", "yes", "on"}

# Optional dependency — all webauthn imports are guarded.
try:
    import webauthn as _webauthn_lib
    from webauthn import (
        generate_registration_options,
        verify_registration_response,
        generate_authentication_options,
        verify_authentication_response,
    )
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria,
        UserVerificationRequirement,
        ResidentKeyRequirement,
        PublicKeyCredentialDescriptor,
    )
    from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
    _WEBAUTHN_AVAILABLE = True
except ImportError:
    _WEBAUTHN_AVAILABLE = False

# In-memory challenge stores (username → base64url-encoded challenge)
_pending_registration_challenges: dict[str, str] = {}
_pending_auth_challenges: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def webauthn_enabled() -> bool:
    """Return True when WebAuthn is enabled."""
    return os.getenv("WEBAUTHN_ENABLED", "false").strip().lower() in _TRUE_VALUES


def _rp_id() -> str:
    return os.getenv("WEBAUTHN_RP_ID", "localhost")


def _rp_name() -> str:
    return os.getenv("WEBAUTHN_RP_NAME", "DocReview360")


def _origin() -> str:
    return os.getenv("WEBAUTHN_ORIGIN", "http://localhost:3000")


# ---------------------------------------------------------------------------
# Credential database
# ---------------------------------------------------------------------------


def _credential_db_path() -> Path:
    try:
        from .auth import _get_user_repository
        user_db = _get_user_repository()._path
        return Path(user_db).with_suffix(".webauthn.db")
    except Exception:
        return Path(os.getenv("DOCREVIEW360_USER_DB", "users.db")).with_suffix(".webauthn.db")


@contextmanager
def _credential_conn() -> Iterator[sqlite3.Connection]:
    db_path = _credential_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            public_key BLOB NOT NULL,
            sign_count INTEGER NOT NULL DEFAULT 0,
            aaguid TEXT,
            transports TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def begin_registration(username: str, display_name: str) -> tuple[str, str]:
    """Begin a WebAuthn registration ceremony.

    Returns ``(options_json, challenge_b64url)``.
    """
    if not _WEBAUTHN_AVAILABLE:
        raise RuntimeError("webauthn package not installed; pip install webauthn")

    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name=_rp_name(),
        user_name=username,
        user_display_name=display_name or username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
    )
    challenge_b64 = bytes_to_base64url(options.challenge)
    _pending_registration_challenges[username] = challenge_b64

    import webauthn.helpers.cbor as _cbor
    options_dict = {
        "rp": {"id": options.rp.id, "name": options.rp.name},
        "user": {
            "id": bytes_to_base64url(options.user.id),
            "name": options.user.name,
            "displayName": options.user.display_name,
        },
        "challenge": challenge_b64,
        "pubKeyCredParams": [
            {"type": "public-key", "alg": p.alg.value}
            for p in options.pub_key_cred_params
        ],
        "timeout": options.timeout,
        "attestation": options.attestation.value if options.attestation else "none",
    }
    return json.dumps(options_dict), challenge_b64


def complete_registration(
    username: str,
    credential_response_json: str,
    challenge_b64url: str,
) -> str:
    """Complete a WebAuthn registration ceremony. Returns the credential ID."""
    if not _WEBAUTHN_AVAILABLE:
        raise RuntimeError("webauthn package not installed; pip install webauthn")

    stored_challenge = _pending_registration_challenges.get(username)
    if not stored_challenge or stored_challenge != challenge_b64url:
        raise ValueError("Invalid or expired registration challenge")

    credential_response = json.loads(credential_response_json)

    verification = verify_registration_response(
        credential=credential_response,
        expected_rp_id=_rp_id(),
        expected_origin=_origin(),
        expected_challenge=base64url_to_bytes(challenge_b64url),
    )

    credential_id = bytes_to_base64url(verification.credential_id)
    transports = credential_response.get("response", {}).get("transports") or []
    aaguid = str(verification.aaguid) if verification.aaguid else None

    now = datetime.now(timezone.utc).isoformat()
    with _credential_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO webauthn_credentials
                (id, username, public_key, sign_count, aaguid, transports, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                credential_id,
                username,
                verification.credential_public_key,
                int(verification.sign_count),
                aaguid,
                json.dumps(transports),
                now,
            ),
        )
        conn.commit()

    _pending_registration_challenges.pop(username, None)
    _logger.info("WebAuthn credential registered for %r: %s", username, credential_id[:16])
    return credential_id


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def begin_authentication(username: str) -> tuple[str, str]:
    """Begin a WebAuthn authentication ceremony.

    Returns ``(options_json, challenge_b64url)``.
    """
    if not _WEBAUTHN_AVAILABLE:
        raise RuntimeError("webauthn package not installed; pip install webauthn")

    # Load existing credentials for the user
    with _credential_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM webauthn_credentials WHERE username = ?", (username,)
        ).fetchall()

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(row["id"]))
        for row in rows
    ]

    options = generate_authentication_options(
        rp_id=_rp_id(),
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    challenge_b64 = bytes_to_base64url(options.challenge)
    _pending_auth_challenges[username] = challenge_b64

    options_dict = {
        "rpId": options.rp_id,
        "challenge": challenge_b64,
        "timeout": options.timeout,
        "allowCredentials": [
            {"type": "public-key", "id": bytes_to_base64url(c.id)}
            for c in (options.allow_credentials or [])
        ],
        "userVerification": options.user_verification.value,
    }
    return json.dumps(options_dict), challenge_b64


def complete_authentication(
    username: str,
    assertion_response_json: str,
    challenge_b64url: str,
) -> bool:
    """Complete a WebAuthn authentication ceremony. Returns True on success."""
    if not _WEBAUTHN_AVAILABLE:
        raise RuntimeError("webauthn package not installed; pip install webauthn")

    stored_challenge = _pending_auth_challenges.get(username)
    if not stored_challenge or stored_challenge != challenge_b64url:
        raise ValueError("Invalid or expired authentication challenge")

    assertion = json.loads(assertion_response_json)
    credential_id_b64 = assertion.get("id") or assertion.get("rawId", "")

    with _credential_conn() as conn:
        row = conn.execute(
            "SELECT public_key, sign_count FROM webauthn_credentials"
            " WHERE id = ? AND username = ?",
            (credential_id_b64, username),
        ).fetchone()

    if row is None:
        raise ValueError("Credential not found for user")

    verification = verify_authentication_response(
        credential=assertion,
        expected_rp_id=_rp_id(),
        expected_origin=_origin(),
        expected_challenge=base64url_to_bytes(challenge_b64url),
        credential_public_key=bytes(row["public_key"]),
        credential_current_sign_count=int(row["sign_count"]),
    )

    # Update sign count
    with _credential_conn() as conn:
        conn.execute(
            "UPDATE webauthn_credentials SET sign_count = ? WHERE id = ? AND username = ?",
            (int(verification.new_sign_count), credential_id_b64, username),
        )
        conn.commit()

    _pending_auth_challenges.pop(username, None)
    return True


# ---------------------------------------------------------------------------
# Credential management
# ---------------------------------------------------------------------------


def list_credentials(username: str) -> list[dict]:
    """Return all registered credentials for ``username``."""
    with _credential_conn() as conn:
        rows = conn.execute(
            "SELECT id, aaguid, transports, created_at FROM webauthn_credentials"
            " WHERE username = ? ORDER BY created_at DESC",
            (username,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "aaguid": row["aaguid"],
            "transports": json.loads(row["transports"] or "[]"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def delete_credential(credential_id: str, username: str) -> bool:
    """Remove a credential. Returns True if it existed and was removed."""
    with _credential_conn() as conn:
        result = conn.execute(
            "DELETE FROM webauthn_credentials WHERE id = ? AND username = ?",
            (credential_id, username),
        )
        conn.commit()
        return result.rowcount > 0
