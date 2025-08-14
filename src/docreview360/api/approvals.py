from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..approvals import get_approval, handle_signature_return
from ..logs import log_event

router = APIRouter()


@router.get("/approvals/return")
async def approval_return(
    signature: str = Query(...),
    approval: str = Query(...),
    certificate_url: Optional[str] = None,
    signed_at: Optional[str] = None,
    next: Optional[str] = Query(None),
):
    """Process provider return parameters for completed signatures."""
    appr = get_approval(approval)
    if appr is None or appr.signature_id != signature:
        log_event(
            "approval_return_invalid",
            approval_id=approval,
            signature_id=signature,
        )
        raise HTTPException(status_code=404, detail="Approval not found")
    log_event(
        "approval_return_received",
        approval_id=approval,
        signature_id=signature,
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
            certificate_url=certificate_url,
            signed_at=signed_at_dt,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if next:
        return RedirectResponse(next)
    return {"status": "processed"}
