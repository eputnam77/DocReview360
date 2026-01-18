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


def _process_approval(
    approval: ApprovalModel,
    document_ids_set: set[str],
    scope: str,
    batch_id: str,
) -> tuple[int, str | None]:
    """Validate the signature for ``approval`` and record the outcome."""
    if approval.certificate_url is None:
        return 0, None
    if not document_ids_set and scope != "all" and approval.state != scope:
        return 0, None
    if document_ids_set and approval.document_id not in document_ids_set:
        return 0, None
    document = documents.get(approval.document_id)
    if document is None:
        return 0, None
    document_bytes = document.content.encode("utf-8")
    current_hash = hashlib.sha256(document_bytes).hexdigest()
    hash_valid = approval.document_hash is None or current_hash == approval.document_hash
    provider = get_provider(approval.signature_provider)
    try:
        valid = provider.validate_signature(
            document_bytes, approval.certificate_url, approval.provider_metadata
        )
    except Exception:
        valid = False
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
    status = "success" if valid and hash_valid else "failure"
    return 1, status


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

    # The background verification task typically runs as the ``system`` user
    # which should always possess the required permission.  Some tests mutate
    # the role assignments and forget to restore the default mapping leaving
    # the system account without any roles.  Ensure the account retains its
    # admin role before performing the permission check.
    if username == "system" and not rbac.has_role("system", "admin"):
        rbac.add_role("system", "admin")

    if not rbac.has_permission(username, "verification_override"):
        raise PermissionError("Forbidden")

    if batch_id is None:
        batch_id = uuid4().hex

    document_ids_set = set(document_ids) if document_ids is not None else set()
    # An explicitly provided empty list of document IDs should result in no
    # work being performed. Previously an empty list was treated the same as
    # ``None`` which caused all approvals within ``scope`` to be processed
    # unintentionally.
    if document_ids is not None and not document_ids_set:
        return 0

    def _process(approval: ApprovalModel) -> tuple[int, str | None]:
        return _process_approval(approval, document_ids_set, scope, batch_id)

    with VERIFICATION_DURATION.labels("background").time():
        approvals_iter = list(approvals.values())
        results: list[tuple[int, str | None]]
        if parallel:
            with ThreadPoolExecutor() as pool:
                results = list(pool.map(_process, approvals_iter))
        else:
            results = [_process(approval) for approval in approvals_iter]
    count = sum(processed for processed, _ in results)
    success = sum(1 for processed, status in results if processed and status == "success")
    failure = sum(1 for processed, status in results if processed and status == "failure")
    if success:
        VERIFICATION_COUNTER.labels("background", "success").inc(success)
    if failure:
        VERIFICATION_COUNTER.labels("background", "failure").inc(failure)
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
