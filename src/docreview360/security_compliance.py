"""Utilities for encryption and data retention checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def xor_encrypt(data: bytes, key: bytes) -> bytes:
    """Return ``data`` encrypted with a repeating-key XOR."""
    if not key:
        raise ValueError("key required")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def xor_decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt XOR-encrypted ``data``."""
    return xor_encrypt(data, key)


def should_purge(created: datetime, retention_days: int) -> bool:
    """Return ``True`` if the item is older than ``retention_days``."""
    if retention_days <= 0:
        raise ValueError("retention_days must be positive")
    # ``created`` timestamps coming from external callers may be naive
    # ``datetime`` objects.  Subtracting a naive value from the timezone aware
    # ``datetime.now(timezone.utc)`` raises ``TypeError`` which previously made
    # the helper unusable for naive inputs.  Treat naive values as UTC so the
    # comparison works consistently.
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created > timedelta(days=retention_days)


def generate_compliance_pdf(data_flow: str) -> bytes:
    """Return a minimal PDF blob describing the data flow."""
    if not data_flow:
        raise ValueError("data_flow required")
    header = b"%PDF-1.4\n"
    # Append a minimal EOF marker so PDF parsers recognise the end of the
    # document.  Without this some viewers refuse to open the generated blob.
    return header + data_flow.encode("utf-8") + b"\n%%EOF\n"
