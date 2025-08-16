from __future__ import annotations

import hashlib
from datetime import timedelta

from docreview360.audit import log_audit_event, schedule_audit_log_purge
from docreview360.approvals import approvals
from docreview360.documents import documents
from docreview360.integrations.signature import get_provider
from docreview360.archive import schedule_archive_purge
from docreview360.settings_manager import load_settings
from docreview360.celery_app import app


def verify_document_signatures(scope: str = "approved") -> int:
    """Recompute hashes and verify signatures for approvals in ``scope``.

    Parameters
    ----------
    scope:
        Either ``"all"`` to process every approval or a specific approval
        ``state`` such as ``"approved"``.

    Returns
    -------
    int
        Number of approvals processed.
    """
    count = 0
    for approval in approvals.values():
        if approval.certificate_url is None:
            continue
        if scope != "all" and approval.state != scope:
            continue
        document = documents.get(approval.document_id)
        if document is None:
            continue
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
        )
        count += 1
    return count


verify_document_signatures = app.task(
    name="docreview360.verify_document_signatures"
)(verify_document_signatures)


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
    schedule_archive_purge()
