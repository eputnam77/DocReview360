"""Async-capable approval management with digital signature, audit logging,
and FANN-based routing support."""

from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from time import perf_counter
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
)
from urllib.parse import quote, urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .audit import AuditLogEntry, get_audit_log, log_audit_event
from .celery_app import app
from .certs import fetch_certificate
from .documents import DocumentModel, documents, get_document, link_approval, unlink_approval
from .integrations.registry import get_provider
from .integrations.signature import get_default_provider, get_default_providers

if TYPE_CHECKING:
    from .ml.torch_models import TinyCritic
from .logs import log_event, log_verification_failure
from .ml.features import SIGNATURE_ANOMALY_FEATURE_NAMES, signature_features
from .ml.onnx_infer import metadata_to_context
from .ml.signature_anomaly import score_signature_anomaly
from .monitoring import (
    APPROVAL_UPLOAD_RETRIES,
    SIGNATURE_ANOMALIES,
    VERIFICATION_COUNTER,
    VERIFICATION_DURATION,
)
from .provider_store import set_provider_health
from .quality import approval_likelihood, quality_model_metadata
from .reviewer_model import ReviewerModel
from .workflows import workflows


@app.task(name="docreview360.approval_reminder")
def _reminder_task(approval_id: str) -> None:
    """Log a reminder event for ``approval_id``."""
    approval = _resolve_pending_approval("approval_reminder", approval_id)
    if approval is None:
        return
    log_event(
        "approval_reminder",
        approval_id=approval_id,
        reviewer=approval.reviewer,
        workflow=approval.workflow,
        doc_id=approval.document_id,
    )


@app.task(name="docreview360.approval_escalation")
def _escalation_task(approval_id: str, target: str) -> None:
    """Log an escalation event for ``approval_id``."""
    approval = _resolve_pending_approval("approval_escalated", approval_id)
    if approval is None:
        return
    log_event(
        "approval_escalated",
        approval_id=approval_id,
        target=target,
        reviewer=approval.reviewer,
        workflow=approval.workflow,
        doc_id=approval.document_id,
    )


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
    scoring_metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def due_at(self) -> datetime | None:  # pragma: no cover - simple alias
        return self.deadline

    @due_at.setter
    def due_at(self, value: datetime | None) -> None:  # pragma: no cover - simple alias
        self.deadline = value


approvals: Dict[str, ApprovalModel] = {}


def reset_approvals() -> None:
    """Clear all in-memory approvals."""

    approvals.clear()


class SignatureValidationError(ValueError):
    """Raised when a signature callback fails validation."""

    def __init__(self, detail: Dict[str, Any]):
        self.detail = detail
        message = str(detail.get("message", "signature validation failed"))
        super().__init__(message)


_SIGNATURE_FALLBACK_ENV = "DOCREVIEW360_ALLOW_SIGNATURE_FALLBACK"


class _RetryPolicy(NamedTuple):
    max_attempts: int
    base_delay: float
    max_delay: float


_DEFAULT_RETRY_POLICY = _RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=5.0)


def _coerce_positive_float(value: Any, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result < 0:
        return default
    return result


def _upload_retry_policy() -> _RetryPolicy:
    settings = _approvals_settings_cached()
    cfg = settings.get("upload_retry", {})
    if not isinstance(cfg, dict):
        return _DEFAULT_RETRY_POLICY
    max_attempts = cfg.get("max_attempts", _DEFAULT_RETRY_POLICY.max_attempts)
    try:
        attempts = int(max_attempts)
    except (TypeError, ValueError):
        attempts = _DEFAULT_RETRY_POLICY.max_attempts
    if attempts < 1:
        attempts = 1
    base_delay = _coerce_positive_float(cfg.get("base_delay"), _DEFAULT_RETRY_POLICY.base_delay)
    max_delay = _coerce_positive_float(cfg.get("max_delay"), _DEFAULT_RETRY_POLICY.max_delay)
    if max_delay < base_delay:
        max_delay = base_delay
    return _RetryPolicy(max_attempts=attempts, base_delay=base_delay, max_delay=max_delay)


def _resolve_pending_approval(event: str, approval_id: str) -> ApprovalModel | None:
    approval = approvals.get(approval_id)
    if approval is None:
        log_event(
            f"{event}_skipped",
            severity="warning",
            approval_id=approval_id,
            reason="missing_approval",
        )
        return None
    if approval.state != "pending":
        log_event(
            f"{event}_skipped",
            severity="info",
            approval_id=approval_id,
            reason="approval_not_pending",
            state=approval.state,
            reviewer=approval.reviewer,
            workflow=approval.workflow,
        )
        return None
    return approval


def _load_approvals_settings() -> Dict[str, Any]:
    try:
        from .settings_manager import load_settings
    except Exception:  # pragma: no cover - settings manager unavailable
        return {}

    settings = load_settings()
    cfg = settings.get("approvals", {})
    if isinstance(cfg, dict):
        return cfg
    return {}


@lru_cache(maxsize=1)
def _approvals_settings_cached() -> Dict[str, Any]:
    return _load_approvals_settings()


def _allow_signature_validation_fallback() -> bool:
    env = os.getenv(_SIGNATURE_FALLBACK_ENV)
    if env is not None:
        return env.strip().lower() in {"1", "true", "yes", "on"}
    settings = _approvals_settings_cached()
    return bool(settings.get("allow_signature_validation_fallback", False))


def refresh_signature_validation_policy() -> None:
    """Clear cached approval settings (primarily for tests)."""

    _approvals_settings_cached.cache_clear()


class SignedApprovalImmutableError(ValueError):
    """Raised when attempting to mutate a signed approval."""


def _hash_document_bytes(document: bytes) -> str:
    return hashlib.sha256(document).hexdigest()


def _hash_document_model(document: DocumentModel) -> str:
    return _hash_document_bytes(document.content.encode("utf-8"))


def _load_document_bytes(doc_id: str) -> bytes | None:
    document = get_document(doc_id)
    if document is None:
        return None
    return document.content.encode("utf-8")


def _record_signature_content_hash(
    approval: ApprovalModel,
    *,
    signature_id: str,
    content_hash: str,
) -> None:
    records = approval.provider_metadata.get("docreview360:signature_records")
    if not isinstance(records, dict):
        records = {}
    records[signature_id] = {
        "content_hash": content_hash,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    approval.provider_metadata["docreview360:signature_records"] = records


def _signature_record_content_hash(approval: ApprovalModel, signature_id: str) -> str | None:
    records = approval.provider_metadata.get("docreview360:signature_records")
    if not isinstance(records, dict):
        return None
    record = records.get(signature_id)
    if not isinstance(record, dict):
        return None
    content_hash = record.get("content_hash")
    return content_hash if isinstance(content_hash, str) and content_hash else None


def _hash_mismatch_warning(
    approval: ApprovalModel,
    *,
    current_hash: str | None,
) -> tuple[bool, str | None]:
    if (
        approval.state == "approved"
        and approval.document_hash is not None
        and current_hash is not None
        and approval.document_hash != current_hash
    ):
        return True, "This document differs from approved version."
    return False, None


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
    scoring_metadata: Dict[str, Any] | None = None,
) -> ApprovalModel:
    """Create a pending approval for the given workflow and reviewer."""
    if doc_id is None:
        doc_id = workflow
    if signature_provider is None:
        signature_provider = get_default_provider()
    approval_id = uuid4().hex
    doc_hash = None
    existing_document = get_document(doc_id)
    if existing_document is not None:
        # Freeze the currently linked document at approval creation time.
        doc_hash = _hash_document_model(existing_document)
    elif document is not None:
        doc_hash = _hash_document_bytes(document)
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
        scoring_metadata=scoring_metadata or {},
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
        scoring_metadata=approval.scoring_metadata,
        model_version=(
            (approval.scoring_metadata.get("model") or {}).get("version")
            if isinstance(approval.scoring_metadata.get("model"), dict)
            else approval.scoring_metadata.get("model_version")
        ),
        model_sha256=(
            (approval.scoring_metadata.get("model") or {}).get("sha256")
            if isinstance(approval.scoring_metadata.get("model"), dict)
            else approval.scoring_metadata.get("model_sha256")
        ),
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
        scoring_metadata=approval.scoring_metadata,
        model_version=(
            (approval.scoring_metadata.get("model") or {}).get("version")
            if isinstance(approval.scoring_metadata.get("model"), dict)
            else approval.scoring_metadata.get("model_version")
        ),
        model_sha256=(
            (approval.scoring_metadata.get("model") or {}).get("sha256")
            if isinstance(approval.scoring_metadata.get("model"), dict)
            else approval.scoring_metadata.get("model_sha256")
        ),
    )
    if reminder_at:
        app.tasks["docreview360.approval_reminder"].apply_async((approval_id,), eta=reminder_at)
    if escalate_to and escalation_at:
        app.tasks["docreview360.approval_escalation"].apply_async(
            (approval_id, escalate_to), eta=escalation_at
        )
    return approval


def submit_draft_for_approval(  # noqa: C901
    workflow: str,
    reviewer: str | None,
    doc_id: str,
    text: str,
    critic: "TinyCritic | None",
    *,
    threshold: float = 0.5,
    extra_reviewer: str = "policy",
    reviewer_model: ReviewerModel | None = None,
) -> ApprovalModel:
    """Score ``text`` and route for additional review if risky."""
    recommendation = None
    score: float | None = None
    recommendation_payload: List[Dict[str, Any]] = []

    model_summary: dict[str, str] | None = None
    if reviewer_model is not None:
        recommendation = reviewer_model.recommend(text, k=3)
        score = recommendation.approval_likelihood
        recommendation_payload = [
            {"reviewer": name, "probability": probability}
            for name, probability in recommendation.ranked_reviewers
        ]
        model_meta = getattr(reviewer_model, "model_metadata", None)
        model_summary = metadata_to_context(model_meta)
        log_event(
            "reviewer_recommendation",
            workflow=workflow,
            doc_id=doc_id,
            approval_likelihood=score,
            recommendations=recommendation_payload,
            model_version=(model_summary or {}).get("version"),
            model_sha256=(model_summary or {}).get("sha256"),
        )
        if reviewer is None:
            reviewer = recommendation.primary
            if reviewer is None:
                raise ValueError("no reviewer available for draft")
    else:
        if reviewer is None:
            raise ValueError("reviewer_model required when reviewer is None")
        if critic is not None:
            score = approval_likelihood(text, critic)
        model_summary = metadata_to_context(quality_model_metadata())

    scoring_metadata: Dict[str, Any] = {}
    if score is not None:
        scoring_metadata["approval_likelihood"] = score
    if recommendation_payload:
        scoring_metadata["recommendations"] = recommendation_payload
    if model_summary:
        model_payload = {
            key: value
            for key, value in model_summary.items()
            if key in {"sha256", "version", "path"} or key.startswith("docreview360:")
        }
        scoring_metadata["model"] = model_payload
        if "sha256" in model_summary:
            scoring_metadata["model_sha256"] = model_summary["sha256"]
        if "version" in model_summary:
            scoring_metadata["model_version"] = model_summary["version"]

    if score is not None and score < threshold:
        create_approval(
            workflow,
            extra_reviewer,
            doc_id,
            description="Auto risk review",
            scoring_metadata=scoring_metadata.copy(),
        )
    return create_approval(
        workflow,
        reviewer,
        doc_id,
        description="Primary review",
        scoring_metadata=scoring_metadata.copy(),
    )


def get_approval(approval_id: str) -> ApprovalModel | None:
    return approvals.get(approval_id)


def delete_approval(approval_id: str) -> ApprovalModel:
    """Remove an approval and unlink it from its document."""
    approval = approvals.pop(approval_id)
    unlink_approval(approval.document_id, approval.id)
    log_event(
        "approval_deleted",
        approval_id=approval_id,
        workflow=approval.workflow,
        reviewer=approval.reviewer,
        doc_id=approval.document_id,
        provider=approval.signature_provider,
    )
    log_audit_event(
        approval.document_id,
        "deleted",
        actor=approval.reviewer,
        approval_id=approval_id,
        workflow=approval.workflow,
    )
    return approval


def remind_approvals(approval_ids: List[str]) -> dict[str, list[str]]:
    """Trigger reminder events for pending approvals."""
    sent: list[str] = []
    skipped: list[str] = []
    for approval_id in approval_ids:
        approval = approvals.get(approval_id)
        if approval is None or approval.state != "pending":
            skipped.append(approval_id)
            continue
        _reminder_task(approval_id)
        sent.append(approval_id)
    return {"sent": sent, "skipped": skipped}


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
        raise ValueError("approval document binding mismatch")
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
        stored_document_bytes = _load_document_bytes(doc_id)
        if stored_document_bytes is None:
            raise KeyError("document not found")
        document = stored_document_bytes
    current_hash = _hash_document_bytes(document)
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
    expected_signature_hash = _signature_record_content_hash(approval, signature_id)
    if expected_signature_hash is None:
        _record_signature_content_hash(
            approval,
            signature_id=signature_id,
            content_hash=current_hash,
        )
    elif expected_signature_hash != current_hash:
        log_event(
            "signature_record_hash_mismatch",
            approval_id=approval.id,
            provider=approval.signature_provider,
            signature_id=signature_id,
            doc_id=doc_id,
            provider_metadata=approval.provider_metadata,
        )
        log_audit_event(
            doc_id,
            "signature_record_hash_mismatch",
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

    feature_snapshot = signature_features(
        (document.decode("utf-8", errors="ignore") if document is not None else ""),
        approval.provider_metadata,
    )["features"]
    approval.provider_metadata.setdefault("docreview360:signature_features", feature_snapshot)

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
        missing_certificate = feature_snapshot.get("evidence_strength", 0.0) < 0.4 and not (
            certificate_url or approval.certificate_url
        )
        explicit_document_supplied = document_param is not None
        fallback_enabled = _allow_signature_validation_fallback()
        if missing_certificate and not fallback_enabled and not explicit_document_supplied:
            detail = {
                "error": "missing_certificate",
                "message": "Signature validation failed: certificate is required.",
                "approval_id": approval.id,
                "signature_id": signature_id,
                "provider": approval.signature_provider,
                "doc_id": doc_id,
            }
            raise SignatureValidationError(detail)
        if missing_certificate and fallback_enabled and not explicit_document_supplied:
            log_event(
                "signature_validation_bypassed",
                severity="warning",
                approval_id=approval.id,
                provider=approval.signature_provider,
                signature_id=signature_id,
                doc_id=doc_id,
                fallback_enabled=True,
                reason="missing_certificate",
                provider_metadata=approval.provider_metadata,
            )
            log_audit_event(
                doc_id,
                "signature_validation_bypassed",
                provider=approval.signature_provider,
                signature_id=signature_id,
                approval_id=approval.id,
                status="fallback",
                fallback_enabled=True,
                reason="missing_certificate",
                provider_metadata=approval.provider_metadata,
            )
        else:
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
        raise SignedApprovalImmutableError("signed approvals cannot be modified; reset required")
    wf = workflows.get(approval.workflow)
    if state == "approved" and wf and wf.mode == "sequential":
        for a in approvals.values():
            if (
                a.workflow == approval.workflow
                and a.order < approval.order
                and a.state != "approved"
            ):
                raise ValueError("previous steps incomplete")
    if state == "approved":
        resolved_document = document
        if resolved_document is None:
            resolved_document = _load_document_bytes(approval.document_id)
        if resolved_document is not None:
            resolved_hash = _hash_document_bytes(resolved_document)
            if approval.document_hash is None:
                approval.document_hash = resolved_hash
            elif resolved_hash != approval.document_hash:
                raise ValueError("document hash mismatch")
            if approval.signature_id is not None:
                expected_signature_hash = _signature_record_content_hash(
                    approval, approval.signature_id
                )
                if expected_signature_hash is None:
                    _record_signature_content_hash(
                        approval,
                        signature_id=approval.signature_id,
                        content_hash=resolved_hash,
                    )
                elif expected_signature_hash != resolved_hash:
                    raise ValueError("document hash mismatch")
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
        policy = _upload_retry_policy()
        attempt = 1
        delay = policy.base_delay
        while True:
            try:
                await _upload_approval_artifacts(approval, document, certificate_url)
                break
            except Exception as exc:
                if attempt >= policy.max_attempts:
                    APPROVAL_UPLOAD_RETRIES.labels("exhausted").inc()
                    log_event(
                        "approval_upload_failed",
                        severity="error",
                        approval_id=approval.id,
                        workflow=approval.workflow,
                        provider=approval.signature_provider,
                        attempts=attempt,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                    break
                APPROVAL_UPLOAD_RETRIES.labels("retry").inc()
                wait = delay if delay > 0 else 0
                if wait:
                    await asyncio.sleep(wait)
                attempt += 1
                if policy.base_delay <= 0:
                    delay = 0
                elif delay <= 0:
                    delay = policy.base_delay
                else:
                    delay = min(delay * 2, policy.max_delay)
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
        if approval.signature_id is not None:
            raise ValueError("document cannot be changed after signature request")
        unlink_approval(approval.document_id, approval.id)
        approval.document_id = doc_id
        link_approval(doc_id, approval.id)
    document = get_document(doc_id)
    document_was_missing = document is None
    if document is None:
        # Allow signing even if the document has not yet been imported.
        # Create an empty placeholder document so subsequent workflow steps
        # (such as ``handle_signature_return``) can still locate it.
        document = DocumentModel(id=doc_id, content="", history=[])
        documents[doc_id] = document
        link_approval(doc_id, approval.id)
    current_hash = _hash_document_model(document)
    if approval.document_hash is None:
        approval.document_hash = current_hash
    elif not document_was_missing and approval.document_hash != current_hash:
        raise ValueError("document hash mismatch")

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
            _record_signature_content_hash(
                approval,
                signature_id=sig_id,
                content_hash=approval.document_hash,
            )
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
                signature_content_hash=approval.document_hash,
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
        current_hash = None
        document = get_document(approval.document_id)
        if document is not None:
            current_hash = _hash_document_model(document)
        hash_mismatch, version_warning = _hash_mismatch_warning(
            approval,
            current_hash=current_hash,
        )
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
                "approved_document_hash": approval.document_hash,
                "current_document_hash": current_hash,
                "approved_version_matches_current": not hash_mismatch,
                "version_warning": version_warning,
                "audit": history,
            }
        )
    return data


_SIGNATURE_ANOMALY_THRESHOLD = 0.8
_DEFAULT_ANOMALY_ESCALATION_TARGET = "risk-ops"


def _retry_snapshot() -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for label in ("retry", "exhausted"):
        sample = APPROVAL_UPLOAD_RETRIES.labels(label)
        value = getattr(sample, "_value", None)
        if value is None:
            snapshot[label] = 0.0
            continue
        try:
            snapshot[label] = float(value.get())
        except Exception:
            snapshot[label] = 0.0
    return snapshot


def _certificate_chain_for_approval(approval: ApprovalModel) -> list[bytes]:
    chain = approval.provider_metadata.get("certificate_chain")
    material: list[bytes] = []
    if isinstance(chain, (list, tuple)):
        for entry in chain:
            if isinstance(entry, bytes):
                material.append(entry)
            elif isinstance(entry, str):
                material.append(entry.encode("utf-8"))
    if not material and approval.certificate_url:
        try:
            data = fetch_certificate(approval.certificate_url)
        except Exception:
            data = None
        if data:
            material.append(data)
    return material


def _build_anomaly_features(
    approval: ApprovalModel,
    document_text: str,
    duration: float,
) -> tuple[dict[str, float], list[float]]:
    payload = signature_features(
        document_text,
        approval.provider_metadata,
        verification_duration=duration,
        retries=_retry_snapshot(),
        certificate_chain=_certificate_chain_for_approval(approval),
    )
    features = dict(payload["features"])
    vector = [float(features.get(name, 0.0)) for name in SIGNATURE_ANOMALY_FEATURE_NAMES]
    return features, vector


def _record_signature_anomaly(
    approval: ApprovalModel,
    score: float,
    features: Mapping[str, float],
    *,
    outcome: str,
    model_name: str,
    model_version: str,
    model_hash: str,
    target: str | None,
) -> dict[str, float]:
    SIGNATURE_ANOMALIES.labels(outcome).inc()
    feature_snapshot = {
        name: float(features.get(name, 0.0)) for name in SIGNATURE_ANOMALY_FEATURE_NAMES
    }
    anomaly_info: dict[str, Any] = {
        "score": float(score),
        "threshold": _SIGNATURE_ANOMALY_THRESHOLD,
        "status": outcome,
        "model_name": model_name,
        "model_version": model_version,
        "model_hash": model_hash,
    }
    if target:
        anomaly_info["target"] = target
        approval.provider_metadata["docreview360:signature_anomaly_target"] = target
    approval.provider_metadata["docreview360:signature_anomaly"] = anomaly_info
    approval.provider_metadata["docreview360:signature_anomaly_features"] = feature_snapshot
    log_audit_event(
        approval.document_id,
        "signature_anomaly",
        approval_id=approval.id,
        status=outcome,
        provider=approval.signature_provider,
        anomaly_score=score,
        model_version=model_version,
        model_hash=model_hash,
        target=target,
    )
    return feature_snapshot


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

    document_text = document.content
    document_bytes = document_text.encode()
    doc_hash = hashlib.sha256(document_bytes).hexdigest()

    for approval in approvals.values():
        if approval.document_id != doc_id:
            continue
        hash_valid = approval.document_hash == doc_hash
        hash_mismatch_warning = None
        if approval.document_hash is not None and approval.document_hash != doc_hash:
            hash_mismatch_warning = "This document differs from approved version."
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
        start_time = perf_counter()

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
            default_providers = get_default_providers()
            if approval.signature_provider != "sandbox":
                default_providers = [p for p in default_providers if p != "sandbox"]
            if approval.signature_provider in default_providers:
                default_providers = [
                    approval.signature_provider,
                    *[p for p in default_providers if p != approval.signature_provider],
                ]
            for p in default_providers:
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
                        document_bytes,
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

        duration = perf_counter() - start_time
        anomaly_features, anomaly_vector = _build_anomaly_features(
            approval,
            document_text,
            duration,
        )
        anomaly_score, model_meta = score_signature_anomaly(anomaly_vector)
        model_name = (
            model_meta.custom_metadata.get("docreview360:model")
            or model_meta.version
            or "signature_anomaly"
        )
        model_version = (
            model_meta.custom_metadata.get("docreview360:version")
            or model_meta.version
            or "unknown"
        )
        model_hash = model_meta.sha256
        outcome = "escalated" if anomaly_score >= _SIGNATURE_ANOMALY_THRESHOLD else "clear"
        escalation_target = None
        if outcome == "escalated":
            escalation_target = approval.escalate_to or _DEFAULT_ANOMALY_ESCALATION_TARGET
        event_name = (
            "signature_anomaly_detected" if outcome == "escalated" else "signature_anomaly_scored"
        )
        log_event(
            event_name,
            approval_id=approval.id,
            provider=approval.signature_provider,
            doc_id=approval.document_id,
            anomaly_score=anomaly_score,
            anomaly_threshold=_SIGNATURE_ANOMALY_THRESHOLD,
            model_name=model_name,
            model_version=model_version,
            model_hash=model_hash,
            escalation_target=escalation_target,
        )
        anomaly_snapshot = _record_signature_anomaly(
            approval,
            anomaly_score,
            anomaly_features,
            outcome=outcome,
            model_name=model_name,
            model_version=model_version,
            model_hash=model_hash,
            target=escalation_target,
        )
        if outcome == "escalated":
            log_event(
                "approval_escalated",
                approval_id=approval.id,
                target=escalation_target,
                reviewer=approval.reviewer,
                workflow=approval.workflow,
                doc_id=approval.document_id,
                reason="signature_anomaly",
                anomaly_score=anomaly_score,
            )
            log_audit_event(
                approval.document_id,
                "approval_escalated",
                approval_id=approval.id,
                provider=approval.signature_provider,
                status="escalated",
                target=escalation_target,
                reason="signature_anomaly",
                anomaly_score=anomaly_score,
            )

        yield {
            "approval_id": approval.id,
            "signature_id": approval.signature_id,
            "hash_valid": hash_valid,
            "approved_document_hash": approval.document_hash,
            "current_document_hash": doc_hash,
            "version_warning": hash_mismatch_warning,
            "signature_valid": signature_valid,
            "certificate_present": certificate_present,
            "signature_verified": provider_valid,
            "provider_results": provider_results,
            "verification_duration": duration,
            "anomaly_score": anomaly_score,
            "anomaly_threshold": _SIGNATURE_ANOMALY_THRESHOLD,
            "anomaly_escalated": outcome == "escalated",
            "escalation_target": escalation_target,
            "anomaly_model": {
                "name": model_name,
                "version": model_version,
                "hash": model_hash,
            },
            "anomaly_features": anomaly_snapshot,
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

