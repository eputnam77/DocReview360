"""Helpers for digital signatures used in approvals."""

from __future__ import annotations

import hashlib
import hmac

from .secrets import get_secret


def _require_secret() -> str:
    """Return the signature secret from configuration or environment."""

    value = get_secret("docreview360_signature_secret")
    if not value:
        raise RuntimeError("DOCREVIEW360_SIGNATURE_SECRET environment variable required")
    return value


def create_signature(data: str, secret: str | None = None) -> str:
    """Return an HMAC-SHA256 signature for ``data``.

    ``secret`` may be explicitly provided.  Passing an empty string should be
    treated as an error rather than silently falling back to the configured
    default secret, which previously happened due to truthiness checks.  This
    ensures callers cannot accidentally verify using the global secret when an
    invalid custom secret was supplied.
    """

    if secret is None:
        secret_value = _require_secret()
    else:
        if not secret:
            raise ValueError("secret must be non-empty")
        secret_value = secret
    return hmac.new(secret_value.encode(), data.encode(), hashlib.sha256).hexdigest()


def verify_signature(data: str, signature: str, secret: str | None = None) -> bool:
    """Verify a signature created with :func:`create_signature`."""
    try:
        expected = create_signature(data, secret)
    except ValueError:
        # ``create_signature`` raises ``ValueError`` when an empty string is
        # supplied for ``secret``.  Verification should be a boolean check
        # rather than propagating the exception; callers expect ``False`` when
        # verification cannot proceed due to an invalid secret.
        return False
    return hmac.compare_digest(expected, signature)
