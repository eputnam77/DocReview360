"""Documenso signature connector.

This module exposes a minimal wrapper around the Documenso REST API. When the
environment variable ``DOCUMENSO_URL`` is defined the functions will perform
HTTP requests against that endpoint. Otherwise an in-memory stub is used so the
rest of the codebase can operate without an external service during tests.
"""

from __future__ import annotations

import hashlib
import os
from base64 import b64encode
from datetime import datetime
from typing import Any, Dict, Tuple
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
from ...secrets import get_secret
from .base import register_provider

# In-memory mapping of signature id -> status
DOCUMENSO_URL = os.getenv("DOCUMENSO_URL")

_signatures: Dict[str, str] = {}
# store workflow id for each signature when provided
_sig_workflows: Dict[str, str] = {}
# map signature id -> certificate url
_sig_certificates: Dict[str, str] = {}
# certificate url -> certificate data
_certificates: Dict[str, Dict[str, Any]] = {}


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

    if DOCUMENSO_URL:
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
            SIGNATURE_FAILURES.labels("documenso").inc()
            raise RuntimeError("Documenso request failed") from exc
    else:
        sig_id = uuid4().hex
        _signatures[sig_id] = "pending"
        url = f"/documenso/{sig_id}"
        meta = {"envelope_id": sig_id}
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


def health_check() -> bool:
    """Return ``True`` if the Documenso service is reachable."""

    if not DOCUMENSO_URL:
        return True
    try:
        resp = http_get(f"{DOCUMENSO_URL.rstrip('/')}/health", timeout=5, headers=_auth_headers())
        return resp.status_code == 200
    except Exception:  # pragma: no cover - network failure
        return False


def complete_signature(sig_id: str) -> None:
    """Mark a signature request as completed either locally or remotely."""
    if DOCUMENSO_URL:
        try:
            resp = http_post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/{sig_id}/complete",
                timeout=5,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("Documenso request failed") from exc
    else:
        if sig_id not in _signatures:
            raise KeyError(f"Unknown signature id {sig_id}")
        _signatures[sig_id] = "signed"

    log_event("signature_completed", entity_id=sig_id)


def verify_signature(signature_id: str, document: bytes) -> bool:
    """Validate ``signature_id`` for ``document``."""
    if DOCUMENSO_URL:
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
    if DOCUMENSO_URL:
        try:
            resp = http_post(
                f"{DOCUMENSO_URL.rstrip('/')}/sign/validate",
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
            raise RuntimeError("Documenso request failed") from exc

    if not certificate_url:
        return False

    cert_info = _certificates.get(certificate_url)
    if not cert_info:
        return False

    cert: x509.Certificate = cert_info["certificate"]
    signature: bytes = cert_info["signature"]
    revoked = cert_info.get("revoked")

    now = datetime.utcnow()
    pub_key = cert.public_key()
    if not isinstance(pub_key, rsa.RSAPublicKey):
        return False
    algo = cert.signature_hash_algorithm
    if algo is None:
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

    if cert.not_valid_before > now or cert.not_valid_after < now:
        return False
    if revoked:
        return False
    if revoked is None and not certs.verify_certificate_status(cert):
        return False
    try:
        pub_key.verify(
            signature,
            document_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
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
    info = {
        "certificate": certificate,
        "signature": signature,
    }
    if revoked is not None:
        info["revoked"] = revoked
    _certificates[url] = info


def signature_status(sig_id: str) -> str:
    """Return the status for ``sig_id``."""
    if DOCUMENSO_URL:
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
        _sig_certificates[sig_id] = str(cert_url)
    if status == "signed":
        wf_id = _sig_workflows.get(sig_id)
        if wf_id:
            try:
                from ...workflows import advance_workflow

                advance_workflow(wf_id)
            except KeyError:
                pass
        try:
            import asyncio

            from ...approvals import handle_signature_return

            coro = handle_signature_return(
                sig_id,
                certificate_url=str(cert_url),
                signed_at=event.signed_at,
            )
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:
                loop.create_task(coro)
        except (KeyError, ValueError):
            pass
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
