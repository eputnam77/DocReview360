from __future__ import annotations

import uuid
from datetime import datetime
from typing import AsyncIterator, Optional

import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from ..approvals import (
    get_approval,
    handle_signature_return,
    verify_document_signature_stream,
)
from ..logs import TRACE_ID, log_call, log_event

router = APIRouter()


@router.get("/approvals/return")
@log_call
async def approval_return(
    request: Request,
    signature: str = Query(...),
    approval: str = Query(...),
    certificate_url: Optional[str] = None,
    signed_at: Optional[str] = None,
    next: Optional[str] = Query(None),
):
    """Process provider return parameters for completed signatures."""
    trace_id = uuid.uuid4().hex
    request.state.trace_id = trace_id
    TRACE_ID.set(trace_id)
    appr = get_approval(approval)
    if appr is None or appr.signature_id != signature:
        log_event(
            "approval_return_invalid",
            approval_id=approval,
            signature_id=signature,
            doc_id=appr.document_id if appr else None,
        )
        raise HTTPException(status_code=404, detail="Approval not found")
    log_event(
        "approval_return_received",
        approval_id=approval,
        signature_id=signature,
        doc_id=appr.document_id,
    )
    signed_at_dt = None
    if signed_at:
        try:
            signed_at_dt = datetime.fromisoformat(signed_at)
        except ValueError:
            signed_at_dt = None
    try:
        handle_signature_return(
            signature,
            doc_id=appr.document_id,
            certificate_url=certificate_url,
            signed_at=signed_at_dt,
            client_ip=request.client.host if request.client else None,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if next:
        return RedirectResponse(next)
    return {"status": "processed"}


@router.get("/documents/{doc_id}/verify-signature/stream")
async def verify_signature_stream(doc_id: str, provider: str | None = None) -> StreamingResponse:
    """Stream signature verification details for ``doc_id``."""
    providers_input: str | list[str] | None = provider
    if provider and "," in provider:
        providers_input = [p.strip() for p in provider.split(",") if p.strip()]

    try:
        gen = verify_document_signature_stream(doc_id, provider=providers_input)
        first_detail = next(gen)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def event_generator() -> AsyncIterator[str]:
        details = [first_detail]
        yield f"data: {json.dumps(first_detail)}\n\n"
        for detail in gen:
            details.append(detail)
            yield f"data: {json.dumps(detail)}\n\n"
        status = (
            "pass"
            if details
            and all(
                d["hash_valid"]
                and d["signature_valid"]
                and d["certificate_present"]
                and d["signature_verified"]
                for d in details
            )
            else "fail"
        )
        yield f"data: {json.dumps({'status': status, 'details': details})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
