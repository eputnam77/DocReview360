from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from docreview360 import rbac
from docreview360.approvals import ApprovalModel, approvals
from docreview360.archive import schedule_archive_purge
from docreview360.audit import (
    log_audit_event,
    schedule_audit_log_hashing,
    schedule_audit_log_purge,
)
from docreview360.celery_app import app
from docreview360.documents import documents
from docreview360.integrations.signature import get_provider
from docreview360.monitoring import VERIFICATION_COUNTER, VERIFICATION_DURATION
from docreview360.settings_manager import load_settings


def verify_document_signatures(
    scope: str = "approved",
    document_ids: list[str] | None = None,
    *,
    parallel: bool = False,
    batch_id: str | None = None,
    username: str = "system",
) -> int:
    """Recompute hashes and verify signatures for approvals.

    Parameters
    ----------
    scope:
        Either ``"all"`` to process every approval or a specific approval
        ``state`` such as ``"approved"``. Ignored when ``document_ids`` is
        provided.
    document_ids:
        Specific document IDs to process.  When ``None`` all approvals within
        ``scope`` are verified.
    parallel:
        When ``True`` approvals are processed concurrently using a thread pool.
    batch_id:
        Optional identifier recorded with each audit log entry.  If omitted a
        unique identifier is generated.

    Returns
    -------
    int
        Number of approvals processed.
    """

    if not rbac.has_permission(username, "verification_override"):
        raise PermissionError("Forbidden")

    if batch_id is None:
        batch_id = uuid4().hex

    document_ids_set = set(document_ids) if document_ids is not None else set()

    def _process(approval: ApprovalModel) -> int:
        if approval.certificate_url is None:
            return 0
        if not document_ids_set and scope != "all" and approval.state != scope:
            return 0
        if document_ids_set and approval.document_id not in document_ids_set:
            return 0
        document = documents.get(approval.document_id)
        if document is None:
            return 0
        document_bytes = document.content.encode("utf-8")
        current_hash = hashlib.sha256(document_bytes).hexdigest()
        hash_valid = approval.document_hash is None or current_hash == approval.document_hash
        provider = get_provider(approval.signature_provider)
        valid = provider.validate_signature(
            document_bytes, approval.certificate_url, approval.provider_metadata
        )
        log_audit_event(
            approval.document_id,
            "signature_validation",
            approval_id=approval.id,
            provider=approval.signature_provider,
            document_hash=current_hash,
            signature_valid=valid,
            hash_valid=hash_valid,
            batch_id=batch_id,
        )
        return 1

    with VERIFICATION_DURATION.labels("background").time():
        approvals_iter = list(approvals.values())
        if parallel:
            with ThreadPoolExecutor() as pool:
                count = sum(pool.map(_process, approvals_iter))
        else:
            count = 0
            for approval in approvals_iter:
                count += _process(approval)
    VERIFICATION_COUNTER.labels("background", "success").inc(count)
    return count


verify_document_signatures = app.task(name="docreview360.verify_document_signatures")(
    verify_document_signatures
)


def schedule_signature_verification() -> None:
    """Configure periodic Celery task based on persisted settings."""
    settings = load_settings()
    cfg = settings.get("signature_verification", {})
    interval = int(cfg.get("interval_minutes", 60))
    scope = str(cfg.get("scope", "approved"))
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["signature_verification"] = {
        "task": "docreview360.verify_document_signatures",
        "schedule": timedelta(minutes=interval),
        "args": (scope,),
    }
    schedule_audit_log_purge()
    schedule_audit_log_hashing()
    schedule_archive_purge()
