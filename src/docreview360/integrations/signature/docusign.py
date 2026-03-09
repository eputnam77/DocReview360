"""DocuSign eSign REST API connector.

This module exposes a minimal wrapper around the DocuSign eSign REST API v2.1.
When the environment variable ``DOCUSIGN_BASE_URL`` is defined the functions
will perform HTTP requests against that endpoint. Otherwise an in-memory stub
is used so the rest of the codebase can operate without an external service
during tests.

Required environment variables when using the live API:
  - ``DOCUSIGN_BASE_URL`` — e.g. ``https://demo.docusign.net/restapi/v2.1``
  - ``DOCUSIGN_ACCOUNT_ID`` — DocuSign account UUID
  - ``DOCUSIGN_INTEGRATION_KEY`` — OAuth integration/application key
  - ``DOCUSIGN_ACCESS_TOKEN`` — Bearer token (or stored via ``get_secret``)
"""

from __future__ import annotations

import logging
import os
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple
from urllib.parse import quote
from uuid import uuid4

import httpx

from ...http_client import get as http_get
from ...http_client import post as http_post
from ...logs import log_event
from ...monitoring import SIGNATURE_FAILURES
from ...provider_store import set_provider_health
from ...secrets import get_secret
from .base import register_provider

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DOCUSIGN_BASE_URL: str | None = os.getenv(
    "DOCUSIGN_BASE_URL", None
)  # e.g. https://demo.docusign.net/restapi/v2.1
_ACCOUNT_ID: str | None = os.getenv("DOCUSIGN_ACCOUNT_ID")
_INTEGRATION_KEY: str | None = os.getenv("DOCUSIGN_INTEGRATION_KEY")


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, 1)


FAILURE_THRESHOLD = _read_int("DOCUSIGN_FAILURE_THRESHOLD", 3)
FAILURE_WINDOW_SECONDS = _read_int("DOCUSIGN_FAILURE_WINDOW_SECONDS", 60)
FAILURE_COOLDOWN_SECONDS = _read_int("DOCUSIGN_FAILURE_COOLDOWN_SECONDS", 300)

# ---------------------------------------------------------------------------
# In-memory stub state
# ---------------------------------------------------------------------------

# signature id -> status string (e.g. "pending", "completed", "voided")
_signatures: Dict[str, str] = {}
# signature id -> workflow id (when provided at request time)
_sig_workflows: Dict[str, str] = {}
# signature id -> envelope metadata dict
_sig_metadata: Dict[str, Dict[str, Any]] = {}

# Circuit-breaker state
_failure_events: deque[datetime] = deque()
_remote_suspended_until: datetime | None = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _auth_headers() -> Dict[str, str]:
    """Return authorization headers using env var or secret store token."""
    token = os.getenv("DOCUSIGN_ACCESS_TOKEN") or get_secret("docusign")
    if token:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    return {"Content-Type": "application/json"}


def _accounts_url() -> str:
    """Return the base accounts URL for the configured account."""
    base = (DOCUSIGN_BASE_URL or "").rstrip("/")
    account_id = _ACCOUNT_ID or ""
    return f"{base}/accounts/{account_id}"


def _set_remote_health_flag(healthy: bool) -> None:
    try:
        set_provider_health("docusign", healthy)
    except Exception as exc:
        _logger.debug("Failed to persist provider health flag (healthy=%s): %s", healthy, exc)


def _reason_label(context: str, exc: httpx.HTTPError) -> str:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        return f"{context}:{status}"
    return f"{context}:{exc.__class__.__name__}"


def _record_failure(reason: str) -> bool:
    """Track a provider failure and return ``True`` when the breaker trips."""
    SIGNATURE_FAILURES.labels("docusign", reason).inc()
    now = _now()
    window = timedelta(seconds=FAILURE_WINDOW_SECONDS)
    _failure_events.append(now)
    while _failure_events and now - _failure_events[0] > window:
        _failure_events.popleft()
    if len(_failure_events) >= FAILURE_THRESHOLD:
        _suspend_remote(reason)
        return True
    return False


def _suspend_remote(trigger: str) -> None:
    """Suspend remote requests for the configured cooldown period."""
    global _remote_suspended_until
    now = _now()
    if _remote_suspended_until and _remote_suspended_until > now:
        return
    _remote_suspended_until = now + timedelta(seconds=FAILURE_COOLDOWN_SECONDS)
    _set_remote_health_flag(False)
    log_event(
        "signature_provider_unhealthy",
        entity_type="signature_provider",
        entity_id="docusign",
        provider="docusign",
        trigger=trigger,
        cooldown_seconds=FAILURE_COOLDOWN_SECONDS,
        severity="warning",
    )


def _handle_remote_http_error(context: str, exc: httpx.HTTPError) -> bool:
    """Record metrics/logs for ``exc`` and return ``True`` if stub should be used."""
    reason = _reason_label(context, exc)
    suspended = _record_failure(reason)
    log_event(
        "signature_provider_failure",
        entity_type="signature",
        entity_id=context,
        provider="docusign",
        reason=reason,
        severity="warning",
    )
    return suspended


def _should_use_remote() -> bool:
    """Return ``True`` when remote DocuSign calls are permitted."""
    if not DOCUSIGN_BASE_URL:
        return False
    global _remote_suspended_until
    if _remote_suspended_until is None:
        return True
    now = _now()
    if now >= _remote_suspended_until:
        _remote_suspended_until = None
        _failure_events.clear()
        _set_remote_health_flag(True)
        log_event(
            "signature_provider_recovered",
            entity_type="signature_provider",
            entity_id="docusign",
            provider="docusign",
        )
        return True
    return False


def _reset_circuit_breaker_for_tests() -> None:  # pragma: no cover - test helper
    _failure_events.clear()
    global _remote_suspended_until
    _remote_suspended_until = None


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


def _create_stub_signature(
    document_id: str,
    user: str,
    workflow_id: str | None,
    approval_id: str | None,
    return_url: str | None,
) -> Tuple[str, str, Dict[str, Any]]:
    sig_id = uuid4().hex
    _signatures[sig_id] = "pending"
    url = f"/docusign/{sig_id}"
    meta: Dict[str, Any] = {"envelope_id": sig_id, "status": "pending"}
    if return_url:
        url += f"?return={quote(return_url)}"
        if approval_id:
            url += f"&approval={quote(approval_id)}"
    if workflow_id:
        _sig_workflows[sig_id] = workflow_id
    _sig_metadata[sig_id] = meta
    log_event(
        "signature_requested",
        user_id=user,
        entity_id=document_id,
        signature_id=sig_id,
        workflow_id=workflow_id,
        approval_id=approval_id,
        provider="docusign",
    )
    return sig_id, url, meta


# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------


def request_signature(
    document_id: str,
    user: str,
    workflow_id: str | None = None,
    *,
    approval_id: str | None = None,
    return_url: str | None = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """Create a DocuSign envelope and return ``(envelope_id, signing_url, metadata)``.

    When ``DOCUSIGN_BASE_URL`` is set the function posts to the DocuSign eSign
    REST API. Otherwise a local in-memory stub record is created. Invalid
    arguments raise ``ValueError``.
    """
    if not document_id or not user:
        raise ValueError("document_id and user are required")

    if _should_use_remote():
        try:
            payload: Dict[str, Any] = {
                "emailSubject": f"Please sign document {document_id}",
                "status": "sent",
                "documents": [
                    {
                        "documentId": "1",
                        "name": document_id,
                        "fileExtension": "pdf",
                        "documentBase64": "",
                    }
                ],
                "recipients": {
                    "signers": [
                        {
                            "email": user if "@" in user else f"{user}@example.com",
                            "name": user,
                            "recipientId": "1",
                            "tabs": {},
                        }
                    ]
                },
            }
            if return_url:
                payload["returnUrl"] = return_url
            if approval_id:
                payload["approvalId"] = approval_id

            resp = http_post(
                f"{_accounts_url()}/envelopes",
                json=payload,
                timeout=10,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            envelope_id: str = data["envelopeId"]

            # Fetch recipient view (embedded signing URL)
            view_payload = {
                "returnUrl": return_url or f"/docusign/{envelope_id}/done",
                "authenticationMethod": "none",
                "email": user if "@" in user else f"{user}@example.com",
                "userName": user,
                "recipientId": "1",
            }
            view_resp = http_post(
                f"{_accounts_url()}/envelopes/{envelope_id}/views/recipient",
                json=view_payload,
                timeout=10,
                headers=_auth_headers(),
            )
            view_resp.raise_for_status()
            signing_url: str = view_resp.json().get("url", f"/docusign/{envelope_id}")
            meta: Dict[str, Any] = {
                "envelope_id": envelope_id,
                "status": data.get("status", "sent"),
            }
        except httpx.HTTPError as exc:
            if _handle_remote_http_error("request_signature", exc):
                return _create_stub_signature(
                    document_id, user, workflow_id, approval_id, return_url
                )
            raise RuntimeError("DocuSign request failed") from exc

        if workflow_id:
            _sig_workflows[envelope_id] = workflow_id
        _signatures[envelope_id] = meta.get("status", "sent")
        _sig_metadata[envelope_id] = meta
        log_event(
            "signature_requested",
            user_id=user,
            entity_id=document_id,
            signature_id=envelope_id,
            workflow_id=workflow_id,
            approval_id=approval_id,
            provider="docusign",
        )
        return envelope_id, signing_url, meta

    return _create_stub_signature(document_id, user, workflow_id, approval_id, return_url)


def process_webhook(data: Dict[str, Any]) -> None:
    """Handle a DocuSign Connect webhook payload.

    DocuSign Connect delivers JSON with camelCase fields. The relevant fields
    are ``envelopeId``, ``status``, and ``completedDateTime``.
    """
    envelope_id = data.get("envelopeId")
    status = data.get("status")
    if not envelope_id or not status:
        raise ValueError("invalid DocuSign webhook payload: missing envelopeId or status")

    _signatures[envelope_id] = status
    completed_at_raw = data.get("completedDateTime")
    completed_at: datetime | None = None
    if completed_at_raw:
        try:
            completed_at = datetime.fromisoformat(str(completed_at_raw).replace("Z", "+00:00"))
        except ValueError:
            _logger.warning("Could not parse completedDateTime %r", completed_at_raw)

    if status == "completed":
        wf_id = _sig_workflows.get(envelope_id)
        if wf_id:
            try:
                from ...workflows import advance_workflow

                advance_workflow(wf_id)
            except KeyError as exc:
                _logger.warning("advance_workflow failed for wf_id %r: %s", wf_id, exc)

        try:
            import asyncio

            from ...approvals import handle_signature_return

            coro = handle_signature_return(
                envelope_id,
                certificate_url=None,
                signed_at=completed_at,
            )
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:
                loop.create_task(coro)
        except (KeyError, ValueError) as exc:
            _logger.warning(
                "handle_signature_return failed for envelope_id %r: %s", envelope_id, exc
            )

    log_event(
        "signature_webhook",
        entity_id=envelope_id,
        status=status,
        provider="docusign",
    )


def verify_signature(signature_id: str, document: bytes) -> bool:
    """Return ``True`` if ``signature_id`` envelope has status ``completed``."""
    if _should_use_remote():
        try:
            resp = http_get(
                f"{_accounts_url()}/envelopes/{signature_id}",
                timeout=10,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            return str(resp.json().get("status", "")) == "completed"
        except httpx.HTTPError as exc:
            if not _handle_remote_http_error("verify_signature", exc):
                raise RuntimeError("DocuSign request failed") from exc

    return _signatures.get(signature_id) == "completed"


def validate_signature(
    document_bytes: bytes,
    certificate_url: str | None,
    metadata: Dict[str, Any],
) -> bool:
    """Return ``True`` if ``metadata`` indicates the envelope is completed."""
    return str(metadata.get("status", "")).lower() == "completed"


def health_check() -> bool:
    """Return ``True`` if the DocuSign service is reachable."""
    if not DOCUSIGN_BASE_URL:
        return True
    if not _should_use_remote():
        return False
    try:
        resp = http_get(
            f"{_accounts_url()}/",
            timeout=10,
            headers=_auth_headers(),
        )
        return int(resp.status_code) == 200
    except Exception as exc:
        _logger.warning("DocuSign health check failed: %s", exc)
        return False


def signature_status(sig_id: str) -> str:
    """Return the current status for ``sig_id``."""
    if _should_use_remote():
        try:
            resp = http_get(
                f"{_accounts_url()}/envelopes/{sig_id}",
                timeout=10,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            return str(resp.json().get("status", "unknown"))
        except httpx.HTTPError as exc:
            raise RuntimeError("DocuSign request failed") from exc
    try:
        return _signatures[sig_id]
    except KeyError as exc:
        raise KeyError(f"Unknown signature id {sig_id}") from exc


# ---------------------------------------------------------------------------
# Provider class
# ---------------------------------------------------------------------------


class DocuSignProvider:
    """Provider wrapper for DocuSign eSign REST API."""

    name = "docusign"

    def request_signature(
        self,
        document_id: str,
        user: str,
        workflow_id: str | None = None,
        *,
        approval_id: str | None = None,
        return_url: str | None = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        return request_signature(
            document_id,
            user,
            workflow_id,
            approval_id=approval_id,
            return_url=return_url,
        )

    def process_webhook(self, data: Dict[str, Any]) -> None:
        process_webhook(data)

    def verify_signature(self, signature_id: str, document: bytes) -> bool:
        return verify_signature(signature_id, document)

    def validate_signature(
        self,
        document_bytes: bytes,
        certificate_url: str | None,
        metadata: Dict[str, Any],
    ) -> bool:
        return validate_signature(document_bytes, certificate_url, metadata)

    def health_check(self) -> bool:
        return health_check()

    def signature_status(self, sig_id: str) -> str:
        return signature_status(sig_id)


# Register provider on import
register_provider(DocuSignProvider())

__all__ = [
    "DOCUSIGN_BASE_URL",
    "request_signature",
    "process_webhook",
    "verify_signature",
    "validate_signature",
    "health_check",
    "signature_status",
    "DocuSignProvider",
]
