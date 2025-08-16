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
    """Return an HMAC-SHA256 signature for ``data`` using ``secret`` if provided."""

    secret_value = secret or _require_secret()
    return hmac.new(secret_value.encode(), data.encode(), hashlib.sha256).hexdigest()


def verify_signature(data: str, signature: str, secret: str | None = None) -> bool:
    """Verify a signature created with :func:`create_signature`."""

    expected = create_signature(data, secret)
    return hmac.compare_digest(expected, signature)
