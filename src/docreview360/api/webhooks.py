from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, HttpUrl, ValidationError

from ..db_store import get_db
from ..http_client import post as http_post
from ..integrations.signature import get_provider
from ..logs import log_call
from ..monitoring import HASH_MISMATCHES, WEBHOOK_DELAY
from ..rbac import require_role
from ..secrets import get_secret

router = APIRouter()

_logger = logging.getLogger(__name__)


class VerificationCompletedEvent(BaseModel):
    """Schema for ``verification.completed`` webhook payloads."""

    doc_id: str
    status: str
    details: List[Dict[str, object]]


class SignatureWebhookPayload(BaseModel):
    """Schema for incoming signature provider webhooks."""

    id: str
    status: str
    certificate_url: HttpUrl | None = None
    signed_at: datetime | None = None


class WebhookSubscription(BaseModel):
    """Subscription request body."""

    url: HttpUrl
    events: List[str]


# ---------------------------------------------------------------------------
# In-memory cache (populated from DB at startup; written through on change)
# ---------------------------------------------------------------------------

_subscribers: Dict[str, List[str]] = {}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _load_subscribers_from_db() -> None:
    """Populate ``_subscribers`` from the ``webhook_subscription_records`` table."""
    global _subscribers
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text(
                    "SELECT event, url FROM webhook_subscription_records WHERE active = 1"
                )
            ).fetchall()
        _subscribers.clear()
        for event, url in rows:
            _subscribers.setdefault(event, []).append(url)
    except Exception as exc:  # pragma: no cover - DB not available
        _logger.warning("Failed to load webhook subscribers from DB: %s", exc)


def _add_subscriber_to_db(event: str, url: str) -> None:
    """Persist a new webhook subscription to the DB."""
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            conn.execute(
                _text(
                    "INSERT INTO webhook_subscription_records (url, event, active)"
                    " VALUES (:url, :event, 1)"
                ),
                {"url": url, "event": event},
            )
    except Exception as exc:  # pragma: no cover - best effort
        _logger.warning("Failed to persist webhook subscription (event=%r, url=%r): %s", event, url, exc)


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------


def _dispatch(event: str, payload: Dict[str, object]) -> None:
    """Send ``payload`` to all subscribers of ``event``."""

    for url in _subscribers.get(event, []):
        try:
            http_post(url, json={"event": event, "payload": payload}, timeout=5)
        except Exception:  # pragma: no cover - best effort
            continue


def emit_verification_completed(doc_id: str, status: str, details: List[Dict[str, object]]) -> None:
    """Trigger a ``verification.completed`` webhook."""

    if "verification.completed" not in _subscribers:
        return
    payload = VerificationCompletedEvent(doc_id=doc_id, status=status, details=details)
    _dispatch("verification.completed", payload.model_dump())


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/webhooks/subscribe", status_code=204, response_class=Response)
@log_call
async def subscribe_webhook(sub: WebhookSubscription, _=Depends(require_role("admin"))) -> Response:
    """Register a webhook callback URL for events."""

    for event in sub.events:
        url_str = str(sub.url)
        _subscribers.setdefault(event, []).append(url_str)
        _add_subscriber_to_db(event, url_str)
    return Response(status_code=204)


@router.post("/hooks", status_code=204, response_class=Response)
@log_call
async def handle_webhook(
    request: Request,
    x_provider: str | None = Header(None, alias="X-Provider"),
    x_signature_provider: str | None = Header(None, alias="X-Signature-Provider"),
    x_signature: str | None = Header(None, alias="X-Signature"),
) -> Response:
    """Dispatch webhook payloads to the appropriate signature provider.

    Provider names must be supplied via headers. Payloads are validated and
    verified using HMAC signatures computed with provider-specific secrets.
    """

    provider_name = x_provider or x_signature_provider
    if not provider_name:
        raise HTTPException(status_code=400, detail="missing provider")
    if not x_signature:
        raise HTTPException(status_code=400, detail="missing signature")

    body = await request.body()
    secret = get_secret(f"{provider_name}_webhook")
    if not secret:
        raise HTTPException(status_code=500, detail="provider secret not configured")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_signature):
        HASH_MISMATCHES.labels(provider_name).inc()
        raise HTTPException(status_code=400, detail="invalid signature")

    try:
        payload_model = SignatureWebhookPayload.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = payload_model.model_dump()

    try:
        get_provider(provider_name).process_webhook(payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload_model.signed_at is not None:
        # Ensure timezone-aware duration calculation
        signed_at = payload_model.signed_at
        if signed_at.tzinfo is None:
            # Treat naive times as UTC for backwards-compat
            signed_at = signed_at.replace(tzinfo=timezone.utc)
        delay = (datetime.now(timezone.utc) - signed_at).total_seconds()
        if delay >= 0:
            WEBHOOK_DELAY.labels(provider_name).observe(delay)

    return Response(status_code=204)
