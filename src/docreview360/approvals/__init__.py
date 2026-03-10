# SPDX-License-Identifier: MIT
"""Approval management package.

All public symbols are re-exported here for backward compatibility so that
existing imports from ``docreview360.approvals`` continue to work unchanged.
"""

from __future__ import annotations

# core: ApprovalModel, in-memory store, CRUD, DB helpers
from .core import (
    ApprovalModel,
    approvals,
    approval_dashboard,
    create_approval,
    delete_approval,
    get_approval,
    get_approval_by_signature,
    list_approvals,
    load_approvals_from_db,
    remind_approvals,
    reset_approval,
    reset_approvals,
    _approval_from_db_data,
    _approval_to_db_data,
    _delete_approval_from_db,
    _hash_mismatch_warning,
    _persist_approval,
)

# signatures: signature logic, PDF building, verification
from .signatures import (
    SignatureValidationError,
    SignedApprovalImmutableError,
    _SIGNATURE_ANOMALY_THRESHOLD,
    _DEFAULT_ANOMALY_ESCALATION_TARGET,
    _SIGNATURE_FALLBACK_ENV,
    _DEFAULT_RETRY_POLICY,
    _RetryPolicy,
    _allow_signature_validation_fallback,
    _approvals_settings_cached,
    _build_anomaly_features,
    _certificate_chain_for_approval,
    _coerce_positive_float,
    _fallback_summary_pdf,
    _hash_document_bytes,
    _hash_document_model,
    _load_approvals_settings,
    _load_document_bytes,
    _merge_pdf_parts,
    _record_signature_anomaly,
    _record_signature_content_hash,
    _retry_snapshot,
    _signature_record_content_hash,
    _upload_approval_artifacts,
    _upload_retry_policy,
    build_approval_pdf,
    build_approvals_summary_pdf,
    get_approval_history,
    get_signed_document,
    handle_signature_return,
    refresh_signature_validation_policy,
    send_for_signature,
    update_approval_state,
    verify_document_hash,
    verify_document_signature,
    verify_document_signature_stream,
)

# routing: Celery tasks, ML scoring, reviewer assignment
from .routing import (
    _escalation_task,
    _reminder_task,
    _resolve_pending_approval,
    run_confirmed_action,
    submit_draft_for_approval,
)

__all__ = [
    # core
    "ApprovalModel",
    "approvals",
    "approval_dashboard",
    "create_approval",
    "delete_approval",
    "get_approval",
    "get_approval_by_signature",
    "list_approvals",
    "load_approvals_from_db",
    "remind_approvals",
    "reset_approval",
    "reset_approvals",
    # signatures
    "SignatureValidationError",
    "SignedApprovalImmutableError",
    "build_approval_pdf",
    "build_approvals_summary_pdf",
    "get_approval_history",
    "get_signed_document",
    "handle_signature_return",
    "refresh_signature_validation_policy",
    "send_for_signature",
    "update_approval_state",
    "verify_document_hash",
    "verify_document_signature",
    "verify_document_signature_stream",
    # routing
    "run_confirmed_action",
    "submit_draft_for_approval",
]
