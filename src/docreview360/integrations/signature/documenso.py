# SPDX-License-Identifier: MIT
"""Documenso signature connector.

This module exposes a minimal wrapper around the Documenso REST API. When the
environment variable ``DOCUMENSO_URL`` is defined the functions will perform
HTTP requests against that endpoint. Otherwise an in-memory stub is used so the
rest of the codebase can operate without an external service during tests.
"""

from __future__ import annotations

import hashlib
import logging
import os
from base64 import b64encode
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, HttpUrl, ValidationError

from ... import certs
from ...http_client import get as http_get
from ...http_client import post as http_post
from ...logs import log_event
from ...monitoring import SIGNATURE_FAILURES

_logger = logging.getLogger(__name__)
from ...provider_store import set_provider_health
from ...secrets import get_secret
from .base import register_provider

# In-memory mapping of signature id -> status
DOCUMENSO_URL = os.getenv("DOCUMENSO_URL")


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, 1)


FAILURE_THRESHOLD = _read_int("DOCUMENSO_FAILURE_THRESHOLD", 3)
FAILURE_WINDOW_SECONDS = _read_int("DOCUMENSO_FAILURE_WINDOW_SECONDS", 60)
FAILURE_COOLDOWN_SECONDS = _read_int("DOCUMENSO_FAILURE_COOLDOWN_SECONDS", 300)

_signatures: Dict[str, str] = {}
# store workflow id for each signature when provided
_sig_workflows: Dict[str, str] = {}
# map signature id -> certificate url
_sig_certificates: Dict[str, str] = {}
# certificate url -> certificate data
_certificates: Dict[str, Dict[str, Any]] = {}
_failure_events: deque[datetime] = deque()
_remote_suspended_until: datetime | None = None


def _normalize_cert_url(url: str) -> str:
    """Return ``url`` with a trailing slash to ensure consistent lookups."""

    parsed = urlparse(url)
    path = parsed.path.rstrip("/") + "/"
    return urlunparse(parsed._replace(path=path))


class DocumensoWebhook(BaseModel):
    id: str
    status: str
    certificate_url: HttpUrl | None = None
    signed_at: datetime | None = None


def _auth_headers() -> Dict[str, str]:
    token = get_secret("documenso")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _set_remote_health_flag(healthy: bool) -> None:
    try:
        set_provider_health("documenso", healthy)
    except Exception as exc:
        # Persisting provider health is best-effort; failures should not mask
        # the original error condition.
        _logger.debug("Failed to persist provider health flag (healthy=%s): %s", healthy, exc)


def _reason_label(context: str, exc: httpx.HTTPError) -> str:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        return f"{context}:{status}"
    return f"{context}:{exc.__class__.__name__}"


def _record_failure(reason: str) -> bool:
    """Track a provider failure and return ``True`` when the breaker trips."""

    SIGNATURE_FAILURES.labels("documenso", reason).inc()
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
        entity_id="documenso",
        provider="documenso",
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
        provider="documenso",
        reason=reason,
        severity="warning",
    )
    return suspended


def _should_use_remote() -> bool:
    """Return ``True`` when remote Documenso calls are permitted."""

    if not DOCUMENSO_URL:
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
            entity_id="documenso",
            provider="documenso",
        )
        return True
    return False


def _complete_signature_stub(sig_id: str, *, allow_create: bool = False) -> None:
    if allow_create and sig_id not in _signatures:
        _signatures[sig_id] = "pending"
    if sig_id not in _signatures:
        raise KeyError(f"Unknown signature id {sig_id}")
    _signatures[sig_id] = "signed"


def _reset_circuit_breaker_for_tests() -> None:  # pragma: no cover - test helper
    _failure_events.clear()
    global _remote_suspended_until
    _remote_suspended_until = None


def _create_stub_signature(
    document_id: str,
    user: str,
    workflow_id: str | None,
    approval_id: str | None,
    return_url: str | None,
) -> Tuple[str, str, Dict[str, Any]]:
    sig_id = uuid4().hex
    _signatures[sig_id] = "pending"
    url = f"/documenso/{sig_id}"
    meta: Dict[str, Any] = {"envelope_id": sig_id}
    if return_url:
        from urllib.parse import quote

        url += f"?return={quote(return_url)}"
        if approval_id:
            url += f"&approval={quote(approval_id)}"
    if workflow_id:
        _sig_workflows[sig_id] = workflow_id
    log_event(
        "signature_requested",
        user_id=user,
        entity_id=document_id,
        signature_id=sig_id,
        workflow_id=workflow_id,
        approval_id=approval_id,
    )
    return sig_id, url, meta


def register_stub_signature(sig_id: str, workflow_id: str | None = None) -> None:
    """Record ``sig_id`` in the local stub registry when created externally."""

    _signatures.setdefault(sig_id, "pending")
    if workflow_id:
        _sig_workflows[sig_id] = workflow_id


def request_signature(
    document_id: str,
    user: str,
    workflow_id: str | None = None,
    *,
    approval_id: str | None = None,
    return_url: str | None = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """Return a signature request id and URL for ``document_id`` issued to ``user``.

    When ``DOCUMENSO_URL`` is defined an HTTP request is sent to the remote
    service. Otherwise a local stub record is created. Invalid arguments raise
    ``ValueError``.
    """

    if not document_id or not user:
        raise ValueError("document_id and user are required")

    if _should_use_remote():
        try:
            payload = {"user": user}
            if return_url:
                payload["return_url"] = return_url
            if approval_id:
                payload["approval_id"] = approval_id
            resp = http_post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{document_id}",
                json=payload,
                timeout=5,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            sig_id = data["id"]
            url = data.get("url", f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}")
            meta = data.get("metadata", {})
        except httpx.HTTPError as exc:
            if _handle_remote_http_error("request_signature", exc):
                return _create_stub_signature(
                    document_id,
                    user,
                    workflow_id,
                    approval_id,
                    return_url,
                )
            raise RuntimeError("Documenso request failed") from exc
        if workflow_id:
            _sig_workflows[sig_id] = workflow_id
        log_event(
            "signature_requested",
            user_id=user,
            entity_id=document_id,
            signature_id=sig_id,
            workflow_id=workflow_id,
            approval_id=approval_id,
        )
        return sig_id, url, meta

    return _create_stub_signature(
        document_id,
        user,
        workflow_id,
        approval_id,
        return_url,
    )


def health_check() -> bool:
    """Return ``True`` if the Documenso service is reachable."""

    if not DOCUMENSO_URL:
        return True
    if not _should_use_remote():
        return False
    url = DOCUMENSO_URL
    try:
        resp = http_get(f"{url.rstrip('/')}/health", timeout=5, headers=_auth_headers())
        return int(resp.status_code) == 200
    except Exception:  # pragma: no cover - network failure
        return False


def complete_signature(sig_id: str) -> None:
    """Mark a signature request as completed either locally or remotely."""
    allow_create = False
    if _should_use_remote():
        try:
            resp = http_post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}/complete",
                timeout=5,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            log_event("signature_completed", entity_id=sig_id)
            return
        except httpx.HTTPError as exc:
            if not _handle_remote_http_error("complete_signature", exc):
                raise RuntimeError("Documenso request failed") from exc
            allow_create = True

    _complete_signature_stub(sig_id, allow_create=allow_create)
    log_event("signature_completed", entity_id=sig_id)


def verify_signature(signature_id: str, document: bytes) -> bool:
    """Validate ``signature_id`` for ``document``."""
    if _should_use_remote():
        try:
            resp = http_post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{signature_id}/verify",
                json={"document": b64encode(document).decode()},
                timeout=5,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            return bool(resp.json().get("valid"))
        except httpx.HTTPError as exc:
            if not _handle_remote_http_error("verify_signature", exc):
                raise RuntimeError("Documenso request failed") from exc
    cert_hash = _sig_certificates.get(signature_id)
    if _signatures.get(signature_id) == "signed" and cert_hash:
        return cert_hash == hashlib.sha256(document).hexdigest()
    return False


def validate_signature(
    document_bytes: bytes,
    certificate_url: str | None,
    metadata: Dict[str, Any],
) -> bool:
    """Perform cryptographic checks on ``document_bytes`` using ``certificate_url``."""
    if _should_use_remote():
        return _remote_validate(document_bytes, certificate_url, metadata)
    return _local_validate(document_bytes, certificate_url)


def _remote_validate(
    document_bytes: bytes, certificate_url: str | None, metadata: Dict[str, Any]
) -> bool:
    """Validate signature against a remote Documenso service."""
    url = DOCUMENSO_URL
    if not url:
        raise RuntimeError("DOCUMENSO_URL not configured")
    try:
        resp = http_post(
            f"{url.rstrip('/')}/sign/validate",
            json={
                "document": b64encode(document_bytes).decode(),
                "certificate_url": certificate_url,
                "metadata": metadata,
            },
            timeout=5,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return bool(resp.json().get("valid"))
    except httpx.HTTPError as exc:
        if _handle_remote_http_error("validate_signature", exc):
            return _local_validate(document_bytes, certificate_url)
        raise RuntimeError("Documenso request failed") from exc


def _local_validate(document_bytes: bytes, certificate_url: str | None) -> bool:
    """Validate signature using locally stored certificate data."""

    if certificate_url:
        certificate_url = _normalize_cert_url(certificate_url)
    if not (certificate_url and (cert_info := _certificates.get(certificate_url))):
        return False

    cert: x509.Certificate = cert_info["certificate"]
    signature: bytes = cert_info["signature"]
    revoked = cert_info.get("revoked")
    pub_key = cert.public_key()
    algo = cert.signature_hash_algorithm
    if not isinstance(pub_key, rsa.RSAPublicKey) or algo is None:
        return False
    try:
        pub_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            algo,
        )
    except Exception:
        return False

    now = datetime.now(timezone.utc)
    not_before = (getattr(cert, "not_valid_before_utc", None) or cert.not_valid_before).replace(
        tzinfo=timezone.utc
    )
    not_after = (getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after).replace(
        tzinfo=timezone.utc
    )
    if not_before > now or not_after < now:
        return False
    if revoked or (revoked is None and not certs.verify_certificate_status(cert)):
        return False
    try:
        pub_key.verify(signature, document_bytes, padding.PKCS1v15(), hashes.SHA256())
    except Exception:
        return False
    return True


def register_test_certificate(
    url: str,
    certificate: x509.Certificate,
    signature: bytes,
    *,
    revoked: bool | None = False,
) -> None:
    """Register a certificate for local validation during tests."""

    normalized = _normalize_cert_url(url)
    info = {
        "certificate": certificate,
        "signature": signature,
    }
    if revoked is not None:
        info["revoked"] = revoked
    _certificates[normalized] = info


def signature_status(sig_id: str) -> str:
    """Return the status for ``sig_id``."""
    if _should_use_remote():
        try:
            resp = http_get(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}",
                timeout=5,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            return str(resp.json()["status"])
        except httpx.HTTPError as exc:
            raise RuntimeError("Documenso request failed") from exc
    try:
        return _signatures[sig_id]
    except KeyError as exc:
        raise KeyError(f"Unknown signature id {sig_id}") from exc


def process_webhook(data: Dict[str, str]) -> None:
    """Process a Documenso webhook payload."""

    try:
        event = DocumensoWebhook.model_validate(data)
    except ValidationError as exc:
        raise ValueError("invalid webhook payload") from exc
    sig_id = event.id
    status = event.status
    _signatures[sig_id] = status
    cert_url = event.certificate_url
    if cert_url:
        _sig_certificates[sig_id] = _normalize_cert_url(str(cert_url))
    if status == "signed":
        wf_id = _sig_workflows.get(sig_id)
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
                sig_id,
                certificate_url=str(cert_url) if cert_url else None,
                signed_at=event.signed_at,
            )
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:
                loop.create_task(coro)
        except (KeyError, ValueError) as exc:
            _logger.warning("handle_signature_return failed for sig_id %r: %s", sig_id, exc)
    log_event("signature_webhook", entity_id=sig_id, status=status)


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
    ) -> Tuple[str, str, Dict[str, Any]]:
        return request_signature(
            document_id,
            user,
            workflow_id,
            approval_id=approval_id,
            return_url=return_url,
        )

    def process_webhook(self, data: dict[str, str]) -> None:
        process_webhook(data)  # pragma: no cover - simple delegation

    def verify_signature(self, signature_id: str, document: bytes) -> bool:
        return verify_signature(signature_id, document)

    def validate_signature(
        self, document_bytes: bytes, certificate_url: str | None, metadata: Dict[str, Any]
    ) -> bool:
        return validate_signature(document_bytes, certificate_url, metadata)

    def health_check(self) -> bool:  # pragma: no cover - simple delegation
        return health_check()


# Register provider on import
register_provider(DocumensoProvider())

__all__ = [
    "DOCUMENSO_URL",
    "request_signature",
    "complete_signature",
    "signature_status",
    "verify_signature",
    "validate_signature",
    "process_webhook",
    "register_test_certificate",
    "DocumensoProvider",
]
