from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import AsyncIterator, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel

from .. import auth
from ..approvals import (
    approval_dashboard,
    build_approval_pdf,
    get_approval,
    get_approval_history,
    get_signed_document,
    handle_signature_return,
    remind_approvals,
    verify_document_hash,
    verify_document_signature_stream,
)
from ..audit import log_audit_event
from ..logs import TRACE_ID, log_call, log_event
from ..rbac import require_permission

router = APIRouter()


class ReminderRequest(BaseModel):
    """Request body for approval reminders."""

    ids: list[str]


def _safe_redirect_path(target: str) -> str | None:
    """Return ``target`` when it is a safe local redirect path."""

    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    return target


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
        await handle_signature_return(
            signature,
            doc_id=appr.document_id,
            certificate_url=certificate_url,
            signed_at=signed_at_dt,
            client_ip=request.client.host if request.client else None,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if next:
        safe_next = _safe_redirect_path(next)
        if safe_next is None:
            raise HTTPException(status_code=400, detail="invalid redirect target")
        return RedirectResponse(safe_next)
    return {"status": "processed"}


@router.get("/approvals/{approval_id}/history")
@log_call
async def approval_history_endpoint(
    approval_id: str,
    user: auth.User = Depends(require_permission("view_audit_log")),
):
    """Return audit history for ``approval_id``."""
    try:
        history = get_approval_history(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [h.model_dump(mode="json") for h in history]


@router.get("/approvals/{approval_id}/signed-document")
@log_call
async def download_signed_document(
    approval_id: str,
    user: auth.User = Depends(require_permission("read")),
) -> Response:
    """Download the document associated with ``approval_id``."""
    try:
        data = get_signed_document(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=data, media_type="application/octet-stream")


@router.get("/approvals/{approval_id}/pdf")
@log_call
async def approval_pdf_endpoint(
    approval_id: str,
    user: auth.User = Depends(require_permission("read")),
) -> Response:
    """Download a combined PDF for ``approval_id``."""
    appr = get_approval(approval_id)
    if appr is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    try:
        data = build_approval_pdf(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_event(
        "approval_pdf_downloaded",
        approval_id=approval_id,
        doc_id=appr.document_id,
        user_id=user.username,
    )
    log_audit_event(
        appr.document_id,
        "approval_pdf_downloaded",
        actor=user.username,
        approval_id=approval_id,
    )
    return Response(content=data, media_type="application/pdf")


@router.get("/approvals/{approval_id}/verify-hash")
@log_call
async def verify_hash_endpoint(
    approval_id: str,
    user: auth.User = Depends(require_permission("verification_override")),
) -> dict[str, bool]:
    """Verify stored document hash for ``approval_id``."""
    try:
        data = get_signed_document(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    valid = verify_document_hash(approval_id, data)
    return {"valid": valid}


@router.post("/approvals/remind")
@log_call
async def remind_approvals_endpoint(body: ReminderRequest) -> dict[str, list[str]]:
    """Trigger reminder events for pending approvals."""
    ids = [aid for aid in body.ids if aid]
    return remind_approvals(ids)


@router.get("/dashboard/approvals")
@log_call
async def dashboard_approvals_endpoint(
    user: auth.User = Depends(require_permission("view_audit_log")),
) -> list[dict[str, object]]:
    """Return approval dashboard data."""
    return approval_dashboard()


@router.get("/documents/{doc_id}/verify-signature/stream")
async def verify_signature_stream(
    doc_id: str,
    provider: str | None = None,
    user: auth.User = Depends(require_permission("verification_override")),
) -> StreamingResponse:
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
