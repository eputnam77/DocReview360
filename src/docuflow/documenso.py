from __future__ import annotations

"""Simple in-memory Documenso signature connector."""

from typing import Dict
from uuid import uuid4

from .logs import log_event


# In-memory mapping of signature id -> status
_signatures: Dict[str, str] = {}


def request_signature(document_id: str, user: str) -> str:
    """Return a signature request id for ``document_id`` issued to ``user``."""
    if not document_id or not user:
        raise ValueError("document_id and user are required")
    sig_id = uuid4().hex
    _signatures[sig_id] = "pending"
    log_event(f"signature_requested:{document_id}:{user}")
    return sig_id


def complete_signature(sig_id: str) -> None:
    """Mark a signature request as completed."""
    if sig_id not in _signatures:
        raise KeyError(f"Unknown signature id {sig_id}")
    _signatures[sig_id] = "signed"
    log_event(f"signature_completed:{sig_id}")


def signature_status(sig_id: str) -> str:
    """Return the status for ``sig_id``."""
    try:
        return _signatures[sig_id]
    except KeyError as exc:
        raise KeyError(f"Unknown signature id {sig_id}") from exc
