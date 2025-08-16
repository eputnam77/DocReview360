from __future__ import annotations

from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, HttpUrl

from ..integrations.signature import get_provider
from ..logs import log_call

router = APIRouter()


class VerificationCompletedEvent(BaseModel):
    """Schema for ``verification.completed`` webhook payloads."""

    doc_id: str
    status: str
    details: List[Dict[str, object]]


class WebhookSubscription(BaseModel):
    """Subscription request body."""

    url: HttpUrl
    events: List[str]


_subscribers: Dict[str, List[str]] = {}


def _dispatch(event: str, payload: Dict[str, object]) -> None:
    """Send ``payload`` to all subscribers of ``event``."""

    for url in _subscribers.get(event, []):
        try:
            httpx.post(url, json={"event": event, "payload": payload}, timeout=5)
        except Exception:  # pragma: no cover - best effort
            continue


def emit_verification_completed(doc_id: str, status: str, details: List[Dict[str, object]]) -> None:
    """Trigger a ``verification.completed`` webhook."""

    if "verification.completed" not in _subscribers:
        return
    payload = VerificationCompletedEvent(doc_id=doc_id, status=status, details=details)
    _dispatch("verification.completed", payload.model_dump())


@router.post("/webhooks/subscribe", status_code=204, response_class=Response)
@log_call
async def subscribe_webhook(sub: WebhookSubscription) -> Response:
    """Register a webhook callback URL for events."""

    for event in sub.events:
        _subscribers.setdefault(event, []).append(str(sub.url))
    return Response(status_code=204)


@router.post("/hooks", status_code=204, response_class=Response)
@log_call
async def handle_webhook(
    payload: dict[str, Any],
    x_provider: str | None = Header(None, alias="X-Provider"),
    x_signature_provider: str | None = Header(None, alias="X-Signature-Provider"),
) -> Response:
    """Dispatch webhook payloads to the appropriate signature provider.

    The provider name can be supplied via the ``X-Provider`` or
    ``X-Signature-Provider`` headers or as ``provider``/``signature_provider``
    keys in the JSON body.
    """

    provider_name = (
        x_provider
        or x_signature_provider
        or payload.get("provider")
        or payload.get("signature_provider")
    )
    if not provider_name:
        raise HTTPException(status_code=400, detail="missing provider")
    try:
        get_provider(provider_name).process_webhook(payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=204)
