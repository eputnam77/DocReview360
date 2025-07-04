"""Documenso signature connector.

This module exposes a minimal wrapper around the Documenso REST API.  When the
environment variable ``DOCUMENSO_URL`` is defined the functions will perform
HTTP requests against that endpoint.  Otherwise an in-memory stub is used so the
rest of the codebase can operate without an external service during tests.
"""

from __future__ import annotations

import os
from typing import Dict
from uuid import uuid4

import httpx

from .logs import log_event

# In-memory mapping of signature id -> status
DOCUMENSO_URL = os.getenv("DOCUMENSO_URL")

_signatures: Dict[str, str] = {}


def request_signature(document_id: str, user: str) -> str:
    """Return a signature request id for ``document_id`` issued to ``user``.

    When ``DOCUMENSO_URL`` is defined an HTTP request is sent to the remote
    service.  Otherwise a local stub record is created.  Invalid arguments raise
    ``ValueError``.
    """

    if not document_id or not user:
        raise ValueError("document_id and user are required")

    if DOCUMENSO_URL:
        try:
            resp = httpx.post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{document_id}",
                json={"user": user},
                timeout=5,
            )
            resp.raise_for_status()
            sig_id = resp.json()["id"]
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            raise RuntimeError("Documenso request failed") from exc
    else:
        sig_id = uuid4().hex
        _signatures[sig_id] = "pending"

    log_event(f"signature_requested:{document_id}:{user}")
    return sig_id


def complete_signature(sig_id: str) -> None:
    """Mark a signature request as completed either locally or remotely."""
    if DOCUMENSO_URL:
        try:
            resp = httpx.post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}/complete", timeout=5
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            raise RuntimeError("Documenso request failed") from exc
    else:
        if sig_id not in _signatures:
            raise KeyError(f"Unknown signature id {sig_id}")
        _signatures[sig_id] = "signed"

    log_event(f"signature_completed:{sig_id}")


def signature_status(sig_id: str) -> str:
    """Return the status for ``sig_id``."""
    if DOCUMENSO_URL:
        try:
            resp = httpx.get(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}", timeout=5
            )
            resp.raise_for_status()
            return resp.json()["status"]
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            raise RuntimeError("Documenso request failed") from exc
    try:
        return _signatures[sig_id]
    except KeyError as exc:
        raise KeyError(f"Unknown signature id {sig_id}") from exc
