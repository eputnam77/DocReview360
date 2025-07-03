"""Helpers for digital signatures used in approvals."""

import hashlib
import hmac

DEFAULT_SECRET = "docuflow"


def create_signature(data: str, secret: str = DEFAULT_SECRET) -> str:
    """Return an HMAC-SHA256 signature for the given data."""
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()


def verify_signature(data: str, signature: str, secret: str = DEFAULT_SECRET) -> bool:
    """Verify a signature created with :func:`create_signature`."""
    expected = create_signature(data, secret)
    return hmac.compare_digest(expected, signature)
