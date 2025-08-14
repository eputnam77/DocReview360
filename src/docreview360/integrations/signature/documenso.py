"""Documenso signature connector.

This module exposes a minimal wrapper around the Documenso REST API. When the
environment variable ``DOCUMENSO_URL`` is defined the functions will perform
HTTP requests against that endpoint. Otherwise an in-memory stub is used so the
rest of the codebase can operate without an external service during tests.
"""

from __future__ import annotations

import os
from typing import Dict, Tuple
from uuid import uuid4

import httpx

from ...logs import log_event
from .base import register_provider

# In-memory mapping of signature id -> status
DOCUMENSO_URL = os.getenv("DOCUMENSO_URL")

_signatures: Dict[str, str] = {}
# store workflow id for each signature when provided
_sig_workflows: Dict[str, str] = {}


def request_signature(
    document_id: str,
    user: str,
    workflow_id: str | None = None,
    *,
    approval_id: str | None = None,
    return_url: str | None = None,
) -> Tuple[str, str]:
    """Return a signature request id and URL for ``document_id`` issued to ``user``.

    When ``DOCUMENSO_URL`` is defined an HTTP request is sent to the remote
    service. Otherwise a local stub record is created. Invalid arguments raise
    ``ValueError``.
    """

    if not document_id or not user:
        raise ValueError("document_id and user are required")

    if DOCUMENSO_URL:
        try:
            payload = {"user": user}
            if return_url:
                payload["return_url"] = return_url
            if approval_id:
                payload["approval_id"] = approval_id
            resp = httpx.post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{document_id}",
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            sig_id = data["id"]
            url = data.get("url", f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}")
        except httpx.HTTPError as exc:
            raise RuntimeError("Documenso request failed") from exc
    else:
        sig_id = uuid4().hex
        _signatures[sig_id] = "pending"
        url = f"/documenso/{sig_id}"
        if return_url:
            from urllib.parse import quote

            url += f"?return={quote(return_url)}"
            if approval_id:
                url += f"&approval={quote(approval_id)}"

    if workflow_id:
        _sig_workflows[sig_id] = workflow_id

    log_event(f"signature_requested:{document_id}:{user}")
    return sig_id, url


def complete_signature(sig_id: str) -> None:
    """Mark a signature request as completed either locally or remotely."""
    if DOCUMENSO_URL:
        try:
            resp = httpx.post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}/complete",
                timeout=5,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
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
            resp = httpx.get(f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}", timeout=5)
            resp.raise_for_status()
            return str(resp.json()["status"])
        except httpx.HTTPError as exc:
            raise RuntimeError("Documenso request failed") from exc
    try:
        return _signatures[sig_id]
    except KeyError as exc:
        raise KeyError(f"Unknown signature id {sig_id}") from exc


def process_webhook(data: Dict[str, str]) -> None:
    """Process a Documenso webhook payload.

    Expected keys are ``id`` and ``status``. When the status is ``signed`` and a
    workflow mapping exists, the workflow is advanced to the next phase.
    """

    sig_id = data.get("id")
    status = data.get("status")
    if not sig_id or not status:
        raise ValueError("invalid webhook payload")
    _signatures[sig_id] = status
    if status == "signed":
        wf_id = _sig_workflows.get(sig_id)
        if wf_id:
            try:
                from ...workflows import advance_workflow

                advance_workflow(wf_id)
            except KeyError:
                pass
        try:
            from ...approvals import handle_signature_return

            signed_at = data.get("signed_at")
            if isinstance(signed_at, str):
                from datetime import datetime

                signed_at_dt = datetime.fromisoformat(signed_at)
            else:
                signed_at_dt = None
            handle_signature_return(
                sig_id,
                certificate_url=data.get("certificate_url"),
                signed_at=signed_at_dt,
            )
        except (KeyError, ValueError):
            pass
    log_event(f"signature_webhook:{sig_id}:{status}")


class DocumensoProvider:
    """Provider wrapper for Documenso."""

    name = "documenso"

    def request_signature(
        self,
        document_id: str,
        user: str,
        workflow_id: str | None = None,
        *,
        approval_id: str | None = None,
        return_url: str | None = None,
    ) -> Tuple[str, str]:
        return request_signature(
            document_id,
            user,
            workflow_id,
            approval_id=approval_id,
            return_url=return_url,
        )

    def process_webhook(self, data: dict) -> None:
        process_webhook(data)  # pragma: no cover - simple delegation


# Register provider on import
register_provider(DocumensoProvider())

__all__ = [
    "DOCUMENSO_URL",
    "request_signature",
    "complete_signature",
    "signature_status",
    "process_webhook",
    "DocumensoProvider",
]
