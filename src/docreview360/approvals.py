"""Async-capable approval management with digital signature, audit logging,
and FANN-based routing support."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .audit import log_audit_event
from .documents import get_document
from .fann_model import Weights
from .integrations.signature import get_default_provider, get_provider
from .logs import log_event
from .quality import approval_likelihood
from .reviewer_model import ReviewerModel
from .workflows import workflows


class ApprovalModel(BaseModel):
    """Representation of an approval record."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    workflow: str
    reviewer: str
    document_id: str
    state: str = "pending"
    due_at: datetime | None = None
    signature_provider: str = Field(default_factory=get_default_provider)
    signature_id: Optional[str] = Field(default=None, alias="signature")
    document_hash: Optional[str] = None
    certificate_url: Optional[str] = None
    signed_at: datetime | None = None
    description: Optional[str] = None
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)


approvals: Dict[str, ApprovalModel] = {}


def create_approval(
    workflow: str,
    reviewer: str,
    doc_id: str,
    due_at: datetime | None = None,
    description: str | None = None,
    *,
    signature_provider: str | None = None,
    document: bytes | None = None,
) -> ApprovalModel:
    """Create a pending approval for the given workflow and reviewer."""
    if signature_provider is None:
        signature_provider = get_default_provider()
    approval_id = uuid4().hex
    doc_hash = hashlib.sha256(document).hexdigest() if document else None
    approval = ApprovalModel(
        id=approval_id,
        workflow=workflow,
        reviewer=reviewer,
        document_id=doc_id,
        due_at=due_at,
        description=description,
        signature_provider=signature_provider,
        document_hash=doc_hash,
    )
    approvals[approval_id] = approval
    log_event(
        "approval_created",
        actor=reviewer,
        workflow=workflow,
        approval_id=approval_id,
        provider=signature_provider,
        document_hash=doc_hash,
        doc_id=doc_id,
        provider_metadata=approval.provider_metadata,
    )
    log_audit_event(
        doc_id,
        "approval_created",
        actor=reviewer,
        workflow=workflow,
        provider=signature_provider,
        document_hash=doc_hash,
        approval_id=approval_id,
        provider_metadata=approval.provider_metadata,
    )
    return approval


def submit_draft_for_approval(
    workflow: str,
    reviewer: str | None,
    doc_id: str,
    text: str,
    weights: Weights,
    *,
    threshold: float = 0.5,
    extra_reviewer: str = "policy",
    reviewer_model: ReviewerModel | None = None,
) -> ApprovalModel:
    """Score ``text`` and route for additional review if risky."""
    score = approval_likelihood(text, weights)
    if score < threshold:
        create_approval(workflow, extra_reviewer, doc_id, description="Auto risk review")
    if reviewer is None:
        if reviewer_model is None:
            raise ValueError("reviewer_model required when reviewer is None")
        reviewer = reviewer_model.route_draft(text)
        if reviewer is None:
            raise ValueError("no reviewer available for draft")
    return create_approval(workflow, reviewer, doc_id, description="Primary review")


def get_approval(approval_id: str) -> ApprovalModel | None:
    return approvals.get(approval_id)


def list_approvals(workflow: str | None = None) -> List[ApprovalModel]:
    if workflow is None:
        return list(approvals.values())
    return [a for a in approvals.values() if a.workflow == workflow]


def get_approval_by_signature(signature_id: str) -> ApprovalModel | None:
    for approval in approvals.values():
        if approval.signature_id == signature_id:
            return approval
    return None


async def handle_signature_return(
    signature_id: str,
    *,
    doc_id: str | None = None,
    document: bytes | None = None,
    certificate_url: str | None = None,
    signed_at: datetime | None = None,
) -> ApprovalModel:
    approval = get_approval_by_signature(signature_id)
    if approval is None:
        raise KeyError("approval not found for signature")
    if doc_id is not None:
        approval.document_id = doc_id
    doc_id = approval.document_id

    log_event(
        "approval_callback",
        approval_id=approval.id,
        provider=approval.signature_provider,
        signature_id=signature_id,
        doc_id=doc_id,
        provider_metadata=approval.provider_metadata,
    )
    log_audit_event(
        doc_id,
        "approval_callback",
        provider=approval.signature_provider,
        signature_id=signature_id,
        approval_id=approval.id,
        provider_metadata=approval.provider_metadata,
    )

    if document is not None and approval.document_hash is not None:
        if hashlib.sha256(document).hexdigest() != approval.document_hash:
            log_event(
                "signature_hash_mismatch",
                approval_id=approval.id,
                provider=approval.signature_provider,
                signature_id=signature_id,
                doc_id=doc_id,
                provider_metadata=approval.provider_metadata,
            )
            log_audit_event(
                doc_id,
                "signature_hash_mismatch",
                provider=approval.signature_provider,
                signature_id=signature_id,
                approval_id=approval.id,
                provider_metadata=approval.provider_metadata,
            )
            raise ValueError("document hash mismatch")

    return await update_approval_state(
        approval.id,
        "approved",
        signature_id=signature_id,
        certificate_url=certificate_url,
        signed_at=signed_at,
        document=document,
    )


async def _upload_approval_artifacts(
    approval: ApprovalModel,
    document: bytes | None,
    certificate_url: str | None,
) -> None:
    if document is not None and approval.document_hash is not None:
        if hashlib.sha256(document).hexdigest() != approval.document_hash:
            raise ValueError("document hash mismatch")

    from .sharepoint import async_client_from_env

    client = await async_client_from_env()
    if document is not None:
        await client.upload_file(f"signed/{approval.id}", document)

    cert_bytes = b""
    if certificate_url:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(certificate_url)
                resp.raise_for_status()
                cert_bytes = resp.content
        except Exception:
            cert_bytes = b""
    if cert_bytes:
        await client.upload_file(f"certificates/{approval.id}", cert_bytes)

    assert approval.signed_at is not None
    props = {
        "signedDate": approval.signed_at.isoformat(),
        "certificateUrl": certificate_url or "",
        "documentHash": approval.document_hash or "",
    }
    await client.set_properties(approval.document_id, props)


async def update_approval_state(
    approval_id: str,
    state: str,
    signature_id: str | None = None,
    *,
    certificate_url: str | None = None,
    signed_at: datetime | None = None,
    due_at: datetime | None = None,
    document: bytes | None = None,
) -> ApprovalModel:
    approval = approvals[approval_id]
    previous = approval.state
    approval.state = state
    if signature_id is not None:
        approval.signature_id = signature_id
    if certificate_url is not None:
        approval.certificate_url = certificate_url
    if due_at is not None:
        approval.due_at = due_at
    if state == "approved":
        approval.signed_at = signed_at or datetime.now(timezone.utc)
        try:
            await _upload_approval_artifacts(approval, document, certificate_url)
        except Exception:
            pass
    else:
        approval.signed_at = None
        approval.certificate_url = None

    wf = workflows.get(approval.workflow)
    project_id = wf.project if wf else ""
    log_event(
        f"approval_{state}",
        actor=approval.reviewer,
        project=project_id,
        approval_id=approval_id,
        provider=approval.signature_provider,
        signature_id=approval.signature_id,
        document_hash=approval.document_hash,
        doc_id=approval.document_id,
        previous_state=previous,
        provider_metadata=approval.provider_metadata,
    )
    log_audit_event(
        approval.document_id,
        state,
        actor=approval.reviewer,
        provider=approval.signature_provider,
        signature_id=approval.signature_id,
        document_hash=approval.document_hash,
        previous_state=previous,
        project=project_id,
        approval_id=approval_id,
        provider_metadata=approval.provider_metadata,
    )

    if state == "approved" and wf:
        if all(
            a.state == "approved" for a in approvals.values() if a.workflow == approval.workflow
        ):
            log_event(
                f"All required approvals completed for project {project_id}",
                project=project_id,
                doc_id=approval.document_id,
            )
    return approval


def send_for_signature(
    approval_id: str,
    doc_id: str,
    user: str,
    return_url: str | None = None,
) -> str:
    approval = approvals[approval_id]
    approval.document_id = doc_id
    if approval.document_hash is None:
        document = get_document(doc_id)
        if document is None:
            raise KeyError("document not found")
        approval.document_hash = hashlib.sha256(document.content.encode("utf-8")).hexdigest()

    callback = f"/approvals/return?approval={approval_id}"
    if return_url:
        callback += f"&next={quote(return_url)}"

    provider = get_provider(approval.signature_provider)
    sig_id, url, meta = provider.request_signature(
        doc_id, user, workflow_id=approval.workflow, approval_id=approval_id, return_url=callback
    )
    approval.signature_id = sig_id
    approval.provider_metadata = meta
    log_event(
        "approval_sent_for_signature",
        actor=user,
        approval_id=approval_id,
        provider=approval.signature_provider,
        signature_id=sig_id,
        workflow=approval.workflow,
        doc_id=doc_id,
        provider_metadata=meta,
    )
    log_audit_event(
        doc_id,
        "sent_for_signature",
        actor=user,
        provider=approval.signature_provider,
        signature_id=sig_id,
        document_hash=approval.document_hash,
        workflow=approval.workflow,
        approval_id=approval_id,
        provider_metadata=meta,
    )
    return url


def verify_document_hash(approval_id: str, document: bytes) -> bool:
    approval = approvals[approval_id]
    if approval.document_hash is None:
        return True
    return approval.document_hash == hashlib.sha256(document).hexdigest()


def verify_document_signature(doc_id: str) -> dict[str, object]:
    document = get_document(doc_id)
    if document is None:
        raise KeyError("document not found")

    doc_hash = hashlib.sha256(document.content.encode()).hexdigest()
    details: list[dict[str, object]] = []

    for approval in approvals.values():
        if approval.document_id != doc_id:
            continue
        hash_valid = approval.document_hash == doc_hash
        signature_valid = approval.state == "approved" and approval.signature_id is not None
        certificate_present = approval.certificate_url is not None
        provider_valid = False
        if approval.signature_id and hash_valid:
            try:
                provider = get_provider(approval.signature_provider)
                provider_valid = provider.verify_signature(
                    approval.signature_id, document.content.encode()
                )
            except Exception:
                provider_valid = False
        details.append(
            {
                "approval_id": approval.id,
                "signature_id": approval.signature_id,
                "hash_valid": hash_valid,
                "signature_valid": signature_valid,
                "certificate_present": certificate_present,
                "signature_verified": provider_valid,
            }
        )

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
    return {"status": status, "details": details}


def reset_approval(
    approval_id: str,
    confirm: bool,
    *,
    username: str,
    password: str,
    otp: str,
    reason: str,
) -> bool:
    from .auth import authenticate_mfa
    from .stubs.task213 import task213

    if not authenticate_mfa(username, password, otp):
        return False

    def _do_reset() -> None:
        approval = approvals.get(approval_id)
        if approval is None:
            raise KeyError("approval not found")
        previous = approval.state
        sig_id = approval.signature_id
        doc_hash = approval.document_hash
        metadata = approval.provider_metadata
        approval.state = "pending"
        approval.signature_id = None
        approval.signed_at = None
        approval.provider_metadata = {}
        log_event(
            "approval_reset",
            actor=username,
            approval_id=approval_id,
            provider=approval.signature_provider,
            doc_id=approval.document_id,
            previous_state=previous,
            reason=reason,
            signature_id=sig_id,
            document_hash=doc_hash,
            provider_metadata=metadata,
        )
        log_audit_event(
            approval.document_id,
            "reset",
            actor=username,
            provider=approval.signature_provider,
            previous_state=previous,
            approval_id=approval_id,
            reason=reason,
            signature_id=sig_id,
            document_hash=doc_hash,
            provider_metadata=metadata,
        )

    return task213(confirm, _do_reset)
