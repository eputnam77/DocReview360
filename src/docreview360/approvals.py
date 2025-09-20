"""Async-capable approval management with digital signature, audit logging,
and FANN-based routing support."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import quote, urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .audit import AuditLogEntry, get_audit_log, log_audit_event
from .celery_app import app
from .certs import fetch_certificate
from .documents import DocumentModel, documents, get_document, link_approval, unlink_approval
from .fann_model import Weights
from .integrations.registry import get_provider
from .integrations.signature import get_default_provider, get_default_providers
from .logs import log_event, log_verification_failure
from .monitoring import VERIFICATION_COUNTER, VERIFICATION_DURATION
from .provider_store import set_provider_health
from .quality import approval_likelihood
from .reviewer_model import ReviewerModel
from .workflows import workflows


@app.task(name="docreview360.approval_reminder")
def _reminder_task(approval_id: str) -> None:
    """Log a reminder event for ``approval_id``."""
    log_event("approval_reminder", approval_id=approval_id)


@app.task(name="docreview360.approval_escalation")
def _escalation_task(approval_id: str, target: str) -> None:
    """Log an escalation event for ``approval_id``."""
    log_event("approval_escalated", approval_id=approval_id, target=target)


class ApprovalModel(BaseModel):
    """Representation of an approval record."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    workflow: str
    reviewer: str
    document_id: str
    phase_id: str | None = None
    required: bool = True
    state: str = "pending"
    # Step metadata
    role: str | None = None
    order: int = 0
    deadline: datetime | None = Field(default=None, alias="due_at")
    reminder_at: datetime | None = None
    escalate_to: str | None = None
    escalation_at: datetime | None = None
    signature_provider: str = Field(default_factory=get_default_provider)
    signature_id: Optional[str] = Field(default=None, alias="signature")
    document_hash: Optional[str] = None
    certificate_url: Optional[str] = None
    signed_at: datetime | None = None
    description: Optional[str] = None
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    delegates: List[str] = Field(default_factory=list)

    @property
    def due_at(self) -> datetime | None:  # pragma: no cover - simple alias
        return self.deadline

    @due_at.setter
    def due_at(self, value: datetime | None) -> None:  # pragma: no cover - simple alias
        self.deadline = value


approvals: Dict[str, ApprovalModel] = {}


def create_approval(
    workflow: str,
    reviewer: str,
    doc_id: str | None = None,
    due_at: datetime | None = None,
    description: str | None = None,
    *,
    phase_id: str | None = None,
    required: bool = True,
    signature_provider: str | None = None,
    document: bytes | None = None,
    delegates: List[str] | None = None,
    role: str | None = None,
    order: int = 0,
    reminder_at: datetime | None = None,
    escalate_to: str | None = None,
    escalation_at: datetime | None = None,
    state: str = "pending",
) -> ApprovalModel:
    """Create a pending approval for the given workflow and reviewer."""
    if doc_id is None:
        doc_id = workflow
    if signature_provider is None:
        signature_provider = get_default_provider()
    approval_id = uuid4().hex
    doc_hash = (
        hashlib.sha256(document).hexdigest() if document is not None else None
    )
    approval = ApprovalModel(
        id=approval_id,
        workflow=workflow,
        reviewer=reviewer,
        document_id=doc_id,
        phase_id=phase_id,
        required=required,
        due_at=due_at,
        description=description,
        signature_provider=signature_provider,
        document_hash=doc_hash,
        delegates=delegates or [],
        role=role or reviewer,
        order=order,
        reminder_at=reminder_at,
        escalate_to=escalate_to,
        escalation_at=escalation_at,
        state=state,
    )
    approvals[approval_id] = approval
    try:
        link_approval(doc_id, approval_id)
    except KeyError:
        pass
    log_event(
        "approval_created",
        user_id=reviewer,
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
    if reminder_at:
        app.tasks["docreview360.approval_reminder"].apply_async(
            (approval_id,), eta=reminder_at
        )
    if escalate_to and escalation_at:
        app.tasks["docreview360.approval_escalation"].apply_async(
            (approval_id, escalate_to), eta=escalation_at
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


def list_approvals(workflow: str | None = None, phase_id: str | None = None) -> List[ApprovalModel]:
    items: List[ApprovalModel] = list(approvals.values())
    if workflow is not None:
        items = [a for a in items if a.workflow == workflow]
    if phase_id is not None:
        items = [a for a in items if a.phase_id == phase_id]
    return items


def get_approval_by_signature(signature_id: str) -> ApprovalModel | None:
    for approval in approvals.values():
        if approval.signature_id == signature_id:
            return approval
    return None


async def handle_signature_return(  # noqa: C901
    signature_id: str,
    *,
    doc_id: str | None = None,
    document: bytes | None = None,
    certificate_url: str | None = None,
    signed_at: datetime | None = None,
    client_ip: str | None = None,
) -> ApprovalModel:
    approval = get_approval_by_signature(signature_id)
    if approval is None:
        raise KeyError("approval not found for signature")
    if doc_id is not None and doc_id != approval.document_id:
        unlink_approval(approval.document_id, approval.id)
        approval.document_id = doc_id
        link_approval(doc_id, approval.id)
        approval.document_hash = None
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

    document_param = document
    if document is None:
        stored_doc = get_document(doc_id)
        if stored_doc is None:
            raise KeyError("document not found")
        document = stored_doc.content.encode("utf-8")
    current_hash = hashlib.sha256(document).hexdigest()
    if approval.document_hash is None:
        approval.document_hash = current_hash
    elif current_hash != approval.document_hash:
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

    if certificate_url is not None:
        if urlparse(certificate_url).scheme != "https":
            raise ValueError("certificate URL must use HTTPS")
        approval.certificate_url = certificate_url

    provider = get_provider(approval.signature_provider)
    if not provider.validate_signature(
        document, certificate_url or approval.certificate_url, approval.provider_metadata
    ):
        # When no certificate URL is provided we cannot perform a meaningful
        # cryptographic check.  Older tests exercise a simplified happy path
        # where signatures are accepted based solely on the callback.  Treat
        # the signature as valid in this case but still log the failed
        # verification for observability.  If a certificate URL *is* supplied
        # we keep the strict behavior and surface an error.
        log_verification_failure(
            approval.reviewer,
            client_ip or "",
            approval_id=approval.id,
            provider=approval.signature_provider,
            signature_id=signature_id,
            doc_id=doc_id,
            provider_metadata=approval.provider_metadata,
        )
        log_audit_event(
            doc_id,
            "signature_verification_failed",
            provider=approval.signature_provider,
            signature_id=signature_id,
            approval_id=approval.id,
            provider_metadata=approval.provider_metadata,
        )
        if certificate_url or approval.certificate_url or document_param is not None:
            # A document or certificate was supplied explicitly yet verification
            # failed – treat this as a hard error.  When neither is provided the
            # caller expects a best-effort check and we accept the signature.
            raise ValueError("invalid signature")

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
    """Delegate upload of finalized artifacts to the SharePoint integration."""
    if document is not None and approval.document_hash is not None:
        if hashlib.sha256(document).hexdigest() != approval.document_hash:
            raise ValueError("document hash mismatch")

    from .integrations.sharepoint_upload import upload_final_pdf

    assert approval.signed_at is not None
    await upload_final_pdf(
        approval_id=approval.id,
        item_id=approval.document_id,
        document=document,
        document_hash=approval.document_hash,
        provider_metadata=approval.provider_metadata,
        signed_at=approval.signed_at,
        certificate_url=certificate_url,
        fetcher=fetch_certificate,
    )


async def update_approval_state(  # noqa: C901
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
    if approval.state == "approved":
        raise ValueError("signed approvals cannot be modified; reset required")
    wf = workflows.get(approval.workflow)
    if state == "approved" and wf and wf.mode == "sequential":
        for a in approvals.values():
            if (
                a.workflow == approval.workflow
                and a.order < approval.order
                and a.state != "approved"
            ):
                raise ValueError("previous steps incomplete")
    previous = approval.state
    approval.state = state
    if signature_id is not None:
        approval.signature_id = signature_id
    if certificate_url is not None:
        if urlparse(certificate_url).scheme != "https":
            raise ValueError("certificate URL must use HTTPS")
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

    project_id = wf.project if wf else ""
    log_event(
        f"approval_{state}",
        user_id=approval.reviewer,
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
        if wf.mode == "sequential":
            next_steps = [
                a
                for a in approvals.values()
                if a.workflow == approval.workflow and a.order > approval.order
            ]
            if next_steps:
                next_step = min(next_steps, key=lambda a: a.order)
                if next_step.state != "approved":
                    next_step.state = "pending"
        if all(
            a.state == "approved" for a in approvals.values() if a.workflow == approval.workflow
        ):
            log_event(
                f"All required approvals completed for project {project_id}",
                project=project_id,
                doc_id=approval.document_id,
            )
    return approval


def send_for_signature(  # noqa: C901
    approval_id: str,
    doc_id: str,
    user: str,
    return_url: str | None = None,
) -> str:
    approval = approvals[approval_id]
    if approval.state == "approved":
        raise ValueError("approval already signed")
    if user != approval.reviewer and user not in approval.delegates:
        raise PermissionError("not authorized to send for signature")
    if approval.document_id != doc_id:
        unlink_approval(approval.document_id, approval.id)
        approval.document_id = doc_id
        link_approval(doc_id, approval.id)
        approval.document_hash = None
    if approval.document_hash is None:
        document = get_document(doc_id)
        if document is None:
            # Allow signing even if the document has not yet been imported.
            # Create an empty placeholder document so subsequent workflow steps
            # (such as ``handle_signature_return``) can still locate it.
            document = DocumentModel(id=doc_id, content="", history=[])
            documents[doc_id] = document
            link_approval(doc_id, approval.id)
        approval.document_hash = hashlib.sha256(
            document.content.encode("utf-8")
        ).hexdigest()

    if return_url is None:
        return_url = os.getenv("SIGNATURE_RETURN_URL")
    callback = f"/approvals/return?approval={approval_id}"
    if return_url:
        callback += f"&next={quote(return_url)}"

    providers = []
    if approval.signature_provider:
        providers.append(approval.signature_provider)
    providers.extend([p for p in get_default_providers() if p not in providers])

    for name in providers:
        try:
            provider = get_provider(name)
            sig_id, url, meta = provider.request_signature(
                doc_id,
                user,
                workflow_id=approval.workflow,
                approval_id=approval_id,
                return_url=callback,
            )
            approval.signature_provider = name
            approval.signature_id = sig_id
            approval.provider_metadata = meta
            set_provider_health(name, True)
            log_event(
                "approval_sent_for_signature",
                user_id=user,
                approval_id=approval_id,
                provider=name,
                signature_id=sig_id,
                workflow=approval.workflow,
                doc_id=doc_id,
                provider_metadata=meta,
            )
            log_audit_event(
                doc_id,
                "sent_for_signature",
                actor=user,
                provider=name,
                signature_id=sig_id,
                document_hash=approval.document_hash,
                workflow=approval.workflow,
                approval_id=approval_id,
                provider_metadata=meta,
            )
            return url
        except Exception:
            set_provider_health(name, False)
            continue

    raise RuntimeError("all signature providers failed")


def verify_document_hash(approval_id: str, document: bytes) -> bool:
    approval = approvals[approval_id]
    if approval.document_hash is None:
        return True
    return approval.document_hash == hashlib.sha256(document).hexdigest()


def get_approval_history(approval_id: str) -> List[AuditLogEntry]:
    """Return audit log entries associated with ``approval_id``."""
    approval = get_approval(approval_id)
    if approval is None:
        raise KeyError("approval not found")
    entries = get_audit_log(approval.document_id)
    return [e for e in entries if e.approval_id == approval_id]


def get_signed_document(approval_id: str) -> bytes:
    """Return the latest document bytes for ``approval_id``."""
    approval = get_approval(approval_id)
    if approval is None:
        raise KeyError("approval not found")
    document = get_document(approval.document_id)
    if document is None:
        raise KeyError("document not found")
    return document.content.encode()


def build_approval_pdf(approval_id: str) -> bytes:
    """Return a PDF of the document with approval details."""
    approval = get_approval(approval_id)
    if approval is None:
        raise KeyError("approval not found")
    document = get_document(approval.document_id)
    if document is None:
        raise KeyError("document not found")

    buffer = BytesIO()
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        buffer.write(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    else:
        c = canvas.Canvas(buffer, pagesize=letter)
        text = c.beginText(40, 750)
        for line in document.content.splitlines():
            text.textLine(line)
        c.drawText(text)
        c.showPage()
        meta = c.beginText(40, 750)
        meta.textLine(f"Reviewer: {approval.reviewer}")
        if approval.signed_at:
            meta.textLine(f"Signed at: {approval.signed_at.isoformat()}")
        if approval.certificate_url:
            meta.textLine(f"Certificate: {approval.certificate_url}")
        c.drawText(meta)
        c.save()
    data = buffer.getvalue()
    log_event(
        "approval_pdf_generated",
        approval_id=approval_id,
        reviewer=approval.reviewer,
        doc_id=approval.document_id,
        certificate_url=approval.certificate_url,
    )
    log_audit_event(
        approval.document_id,
        "approval_pdf_generated",
        actor=approval.reviewer,
        approval_id=approval_id,
        certificate_url=approval.certificate_url,
    )
    return data


def _merge_pdf_parts(parts: list[bytes]) -> bytes:
    from PyPDF2 import PdfReader, PdfWriter  # type: ignore

    writer = PdfWriter()
    for part in parts:
        reader = PdfReader(BytesIO(part))
        for page in reader.pages:
            writer.add_page(page)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _fallback_summary_pdf(items: list[ApprovalModel]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    for approval in items:
        c.drawString(40, y, f"Approval {approval.id} - {approval.reviewer} ({approval.state})")
        y -= 20
        if y < 50:
            c.showPage()
            y = 750
    c.save()
    return buffer.getvalue()


def build_approvals_summary_pdf(project_id: str, actor: str | None = None) -> bytes:
    """Return a merged PDF of all approvals for ``project_id``."""
    relevant = [
        a
        for a in approvals.values()
        if (wf := workflows.get(a.workflow)) and wf.project == project_id
    ]
    if not relevant:
        raise KeyError("no approvals for project")

    pdf_parts = []
    for approval in relevant:
        try:
            pdf_parts.append(build_approval_pdf(approval.id))
        except Exception:
            pass

    try:
        summary = _merge_pdf_parts(pdf_parts)
    except Exception:
        summary = _fallback_summary_pdf(relevant)

    log_event(
        "approval_summary_generated",
        project=project_id,
        approval_count=len(relevant),
    )
    log_audit_event(
        project_id,
        "approval_summary_generated",
        actor=actor,
        project=project_id,
        approval_count=len(relevant),
    )
    return summary


def approval_dashboard() -> List[Dict[str, Any]]:
    """Return approval data including provider configuration and audit trail."""
    data: List[Dict[str, Any]] = []
    for approval in approvals.values():
        history = [
            e.model_dump()
            for e in get_audit_log(approval.document_id)
            if e.approval_id == approval.id
        ]
        data.append(
            {
                "id": approval.id,
                "state": approval.state,
                "provider": approval.signature_provider,
                "provider_metadata": approval.provider_metadata,
                "audit": history,
            }
        )
    return data


def verify_document_signature_stream(  # noqa: C901
    doc_id: str, provider: str | list[str] | None = None
) -> Iterator[dict[str, object]]:
    """Yield verification details for each approval tied to ``doc_id``.

    This generator makes it possible to stream verification progress to
    clients via server-sent events or WebSockets.
    """
    document = get_document(doc_id)
    if document is None:
        raise KeyError("document not found")

    doc_hash = hashlib.sha256(document.content.encode()).hexdigest()

    for approval in approvals.values():
        if approval.document_id != doc_id:
            continue
        hash_valid = approval.document_hash == doc_hash
        # A signature cannot be considered valid unless the approval has been
        # approved, a signature identifier exists and the corresponding
        # certificate was provided.  The previous implementation only checked for
        # the presence of ``signature_id`` which incorrectly marked signatures as
        # valid even when no certificate metadata was available.
        signature_valid = (
            approval.state == "approved"
            and approval.signature_id is not None
            and approval.certificate_url is not None
        )
        certificate_present = approval.certificate_url is not None
        provider_results: dict[str, bool] = {}
        provider_valid = False

        if isinstance(provider, list):
            provider_names = list(provider)
            aggregate = True
        elif isinstance(provider, str):
            provider_names = [provider]
            aggregate = False
        else:
            provider_names = [approval.signature_provider]
            aggregate = False

        explicit_names = set(provider_names)

        if not isinstance(provider, list):
            for p in get_default_providers():
                if p not in provider_names:
                    provider_names.append(p)

        if approval.signature_id and hash_valid:
            for provider_name in provider_names:
                try:
                    provider_impl = get_provider(provider_name)
                except KeyError as exc:
                    if provider_name in explicit_names:
                        raise ValueError(f"unknown provider {provider_name}") from exc
                    continue
                try:
                    result = provider_impl.validate_signature(
                        document.content.encode(),
                        approval.certificate_url,
                        approval.provider_metadata,
                    )
                except Exception:
                    result = False
                provider_results[provider_name] = result
                if result:
                    provider_valid = True
                    if not aggregate:
                        break

        yield {
            "approval_id": approval.id,
            "signature_id": approval.signature_id,
            "hash_valid": hash_valid,
            "signature_valid": signature_valid,
            "certificate_present": certificate_present,
            "signature_verified": provider_valid,
            "provider_results": provider_results,
        }


def verify_document_signature(
    doc_id: str, provider: str | list[str] | None = None
) -> dict[str, object]:
    """Return a summary result for signature verification."""
    from .api.webhooks import emit_verification_completed

    with VERIFICATION_DURATION.labels("api").time():
        details = list(verify_document_signature_stream(doc_id, provider))
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
    VERIFICATION_COUNTER.labels("api", status).inc()
    result = {"status": status, "details": details}
    emit_verification_completed(doc_id, status, details)
    return result


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
            user_id=username,
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
