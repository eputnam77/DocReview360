# SPDX-License-Identifier: MIT
"""Webhook subscription management and outgoing delivery with HMAC-SHA256 signing."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
    # Optional shared secret for HMAC-SHA256 signing; auto-generated if omitted
    secret: Optional[str] = None


class WebhookSubscriptionResponse(BaseModel):
    """Response for a created/listed subscription."""

    id: int
    url: str
    events: List[str]
    # Returned once on creation so the caller can store it; never shown again
    secret: Optional[str] = None


# ---------------------------------------------------------------------------
# In-memory cache: event → list of (url, signing_secret | None, db_id)
# ---------------------------------------------------------------------------

_subscribers: Dict[str, List[tuple[str, str | None, int]]] = {}


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
                    "SELECT id, event, url, signing_secret"
                    " FROM webhook_subscription_records WHERE active = 1"
                )
            ).fetchall()
        _subscribers.clear()
        for row_id, event, url, signing_secret in rows:
            _subscribers.setdefault(event, []).append((url, signing_secret, row_id))
    except Exception as exc:  # pragma: no cover - DB not available
        _logger.warning("Failed to load webhook subscribers from DB: %s", exc)


def _add_subscriber_to_db(event: str, url: str, signing_secret: str | None) -> int:
    """Persist a new webhook subscription to the DB and return its row id."""
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            result = conn.execute(
                _text(
                    "INSERT INTO webhook_subscription_records (url, event, active, signing_secret)"
                    " VALUES (:url, :event, 1, :secret)"
                ),
                {"url": url, "event": event, "secret": signing_secret},
            )
            return result.lastrowid or 0
    except Exception as exc:  # pragma: no cover - best effort
        _logger.warning(
            "Failed to persist webhook subscription (event=%r, url=%r): %s", event, url, exc
        )
        return 0


def _update_delivery_stats(row_id: int, success: bool) -> None:
    """Update delivery count and last delivery status for a subscription."""
    try:
        from sqlalchemy import text as _text

        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        status = "ok" if success else "failed"
        with db.session() as conn:
            conn.execute(
                _text(
                    "UPDATE webhook_subscription_records"
                    " SET delivery_count = delivery_count + 1,"
                    "     last_delivery_at = :now,"
                    "     last_status = :status"
                    " WHERE id = :row_id"
                ),
                {"now": now, "status": status, "row_id": row_id},
            )
    except Exception:  # pragma: no cover - best effort
        pass


# ---------------------------------------------------------------------------
# Signing helpers
# ---------------------------------------------------------------------------

SIGNATURE_HEADER = "X-DocReview360-Signature"
SIGNATURE_ALGORITHM = "sha256"


def _sign_payload(body: bytes, secret: str) -> str:
    """Return the HMAC-SHA256 signature header value for ``body``.

    Format: ``sha256=<hex-digest>`` — same convention as GitHub webhooks.
    """
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_ALGORITHM}={digest}"


def verify_incoming_signature(body: bytes, signature: str, secret: str) -> bool:
    """Return True if ``signature`` matches the HMAC-SHA256 of ``body``."""
    expected = _sign_payload(body, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------


def _dispatch(event: str, payload: Dict[str, object]) -> None:
    """Deliver ``payload`` to all subscribers of ``event`` with HMAC-SHA256 signing.

    Each outgoing request includes:
    - ``X-DocReview360-Signature: sha256=<hmac>`` when a signing secret is set
    - ``X-DocReview360-Event: <event>``
    - ``X-DocReview360-Delivery: <random-hex>`` (unique delivery ID for deduplication)
    """
    body = json.dumps({"event": event, "payload": payload}).encode("utf-8")
    delivery_id = secrets.token_hex(16)

    for url, signing_secret, row_id in _subscribers.get(event, []):
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-DocReview360-Event": event,
            "X-DocReview360-Delivery": delivery_id,
        }
        if signing_secret:
            headers[SIGNATURE_HEADER] = _sign_payload(body, signing_secret)

        success = False
        try:
            resp = http_post(url, data=body, headers=headers, timeout=5)
            success = resp.status_code < 400
            if not success:
                _logger.warning(
                    "Webhook delivery to %s returned %d for event %r",
                    url, resp.status_code, event,
                )
        except Exception as exc:  # pragma: no cover - network errors
            _logger.warning("Webhook delivery to %s failed: %s", url, exc)
        finally:
            if row_id:
                _update_delivery_stats(row_id, success)


def emit_verification_completed(doc_id: str, status: str, details: List[Dict[str, object]]) -> None:
    """Trigger a ``verification.completed`` webhook."""

    if "verification.completed" not in _subscribers:
        return
    payload = VerificationCompletedEvent(doc_id=doc_id, status=status, details=details)
    _dispatch("verification.completed", payload.model_dump())


def emit_lifecycle_event(event: str, data: Dict[str, object]) -> None:
    """Deliver a lifecycle event to all subscribers.

    Supported lifecycle events:
    - ``document.created``
    - ``document.updated``
    - ``document.deleted``
    - ``approval.requested``
    - ``approval.completed``
    - ``approval.rejected``
    - ``project.created``
    - ``project.updated``
    - ``workflow.status``
    - ``workflow.completed``
    """
    if event not in _subscribers:
        return
    _dispatch(event, data)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/webhooks/subscribe", response_model=WebhookSubscriptionResponse)
@log_call
async def subscribe_webhook(
    sub: WebhookSubscription, _=Depends(require_role("admin"))
) -> WebhookSubscriptionResponse:
    """Register a webhook callback URL for one or more lifecycle events.

    A signing secret is auto-generated if not supplied.  **Store the returned
    ``secret`` — it is only shown once.**  Use it to verify the
    ``X-DocReview360-Signature`` header on incoming deliveries.
    """
    # Generate a signing secret if the caller did not supply one
    signing_secret = sub.secret or secrets.token_hex(32)

    added_events: list[str] = []
    last_id = 0
    for event in sub.events:
        url_str = str(sub.url)
        row_id = _add_subscriber_to_db(event, url_str, signing_secret)
        _subscribers.setdefault(event, []).append((url_str, signing_secret, row_id))
        added_events.append(event)
        last_id = row_id

    return WebhookSubscriptionResponse(
        id=last_id,
        url=str(sub.url),
        events=added_events,
        secret=signing_secret,
    )


@router.get("/webhooks/subscriptions")
@log_call
async def list_webhook_subscriptions(_=Depends(require_role("admin"))) -> list[dict]:
    """List all active webhook subscriptions."""
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text(
                    "SELECT id, url, event, delivery_count, last_delivery_at, last_status"
                    " FROM webhook_subscription_records WHERE active = 1"
                    " ORDER BY id"
                )
            ).fetchall()
        return [
            {
                "id": r[0],
                "url": r[1],
                "event": r[2],
                "delivery_count": r[3],
                "last_delivery_at": str(r[4]) if r[4] else None,
                "last_status": r[5],
            }
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/webhooks/subscriptions/{sub_id}", status_code=204, response_class=Response)
@log_call
async def delete_webhook_subscription(
    sub_id: int, _=Depends(require_role("admin"))
) -> Response:
    """Deactivate a webhook subscription by ID."""
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            conn.execute(
                _text("UPDATE webhook_subscription_records SET active = 0 WHERE id = :id"),
                {"id": sub_id},
            )
        # Refresh in-memory cache
        _load_subscribers_from_db()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/hooks", status_code=204, response_class=Response)
@log_call
async def handle_webhook(
    request: Request,
    x_provider: str | None = Header(None, alias="X-Provider"),
    x_signature_provider: str | None = Header(None, alias="X-Signature-Provider"),
    x_signature: str | None = Header(None, alias="X-Signature"),
) -> Response:
    """Dispatch incoming signature provider webhooks to the appropriate handler.

    Provider names must be supplied via headers.  Payloads are validated and
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
        signed_at = payload_model.signed_at
        if signed_at.tzinfo is None:
            signed_at = signed_at.replace(tzinfo=timezone.utc)
        delay = (datetime.now(timezone.utc) - signed_at).total_seconds()
        if delay >= 0:
            WEBHOOK_DELAY.labels(provider_name).observe(delay)

    return Response(status_code=204)
