from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Response

from ..integrations.signature import get_provider
from ..logs import log_call

router = APIRouter()


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
