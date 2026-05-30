# SPDX-License-Identifier: MIT
"""Core approval CRUD: ApprovalModel, in-memory store, DB persistence."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..audit import log_audit_event
from ..db_store import get_db
from ..documents import DocumentModel, get_document, link_approval, unlink_approval
from ..integrations.signature import get_default_provider
from ..logs import log_event

_logger = logging.getLogger(__name__)


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

# ---------------------------------------------------------------------------
# B-01/B-02: Per-approval async locks
# ---------------------------------------------------------------------------

_approval_locks: Dict[str, asyncio.Lock] = {}


def get_approval_lock(approval_id: str) -> asyncio.Lock:
    """Return (creating if necessary) the async lock for *approval_id*."""
    if approval_id not in _approval_locks:
        _approval_locks[approval_id] = asyncio.Lock()
    return _approval_locks[approval_id]


def release_approval_lock(approval_id: str) -> None:
    """Remove the lock for *approval_id* from the registry (call on delete)."""
    _approval_locks.pop(approval_id, None)


# ---------------------------------------------------------------------------
# B-08: Secondary index — (workflow, phase_id) → [approval_id, ...]
# ---------------------------------------------------------------------------

_workflow_approvals: Dict[str, List[str]] = {}


def _wa_key(workflow: str, phase_id: str | None) -> str:
    return f"{workflow}:{phase_id or ''}"


def get_approvals_for_workflow(
    workflow: str, phase_id: str | None = None
) -> List[ApprovalModel]:
    """Return all approvals for *workflow* (optionally scoped to *phase_id*)."""
    key = _wa_key(workflow, phase_id)
    ids = _workflow_approvals.get(key, [])
    return [approvals[aid] for aid in ids if aid in approvals]


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------


def _approval_to_db_data(approval: ApprovalModel) -> Dict[str, Any]:
    """Serialise an :class:`ApprovalModel` for JSON storage."""
    data = approval.model_dump(by_alias=False)
    # datetime fields must be ISO strings for JSON
    for field in ("deadline", "reminder_at", "escalation_at", "signed_at"):
        val = data.get(field)
        if val is not None and hasattr(val, "isoformat"):
            data[field] = val.isoformat()
    return data


def _normalize_phase_scope(phase_id: str | None) -> str:
    return phase_id or ""


def _approval_order_conflict_message(approval: ApprovalModel) -> str:
    return (
        f"An approval with order={approval.order} already exists in workflow "
        f"'{approval.workflow}' phase '{approval.phase_id}'"
    )


def _approval_from_db_data(data: Dict[str, Any]) -> ApprovalModel:
    """Deserialise an :class:`ApprovalModel` from JSON storage."""
    return ApprovalModel.model_validate(data)


def _persist_approval(
    approval: ApprovalModel, previous: ApprovalModel | None = None
) -> None:
    """Upsert *approval* into the ``approval_records`` table.

    B-07: If the DB write fails and *previous* is provided, the in-memory store
    is restored to *previous* so the dict never holds a state that is not
    durable.
    """
    conn_ref: Any = None
    try:
        from sqlalchemy import text as _text

        db = get_db()
        data = _approval_to_db_data(approval)
        with db.session() as conn:
            conn_ref = conn
            conn.execute(
                _text(
                    "INSERT INTO approval_records ("
                    "id, workflow_id, phase_id, reviewer, state, approval_order, data"
                    ") VALUES (:id, :wf, :phase_id, :rev, :st, :approval_order, :data)"
                    " ON CONFLICT(id) DO UPDATE SET workflow_id=excluded.workflow_id,"
                    " phase_id=excluded.phase_id, reviewer=excluded.reviewer,"
                    " state=excluded.state, approval_order=excluded.approval_order,"
                    " data=excluded.data"
                ),
                {
                    "id": approval.id,
                    "wf": approval.workflow,
                    "phase_id": _normalize_phase_scope(approval.phase_id),
                    "rev": approval.reviewer,
                    "st": approval.state,
                    "approval_order": approval.order,
                    "data": json.dumps(data),
                },
            )
            conn_ref = None  # session committed successfully
    except Exception as exc:
        try:
            if conn_ref is not None:
                conn_ref.rollback()
        except Exception:
            pass
        if previous is not None:
            approvals[approval.id] = previous
        message = str(exc).lower()
        if "uq_approval_records_workflow_phase_order" in message or (
            "approval_records.workflow_id" in message
            and "approval_records.phase_id" in message
            and "approval_records.approval_order" in message
        ):
            raise ValueError(_approval_order_conflict_message(approval)) from exc
        _logger.error("Failed to persist approval %r to DB: %s", approval.id, exc)


def _ensure_unique_order_in_db(workflow: str, phase_id: str | None, order: int) -> None:
    """Check persisted approvals so duplicate order values fail before insert."""

    if order == 0:
        return
    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        row = conn.execute(
            _text(
                "SELECT id FROM approval_records"
                " WHERE workflow_id = :wf AND phase_id = :phase_id AND approval_order = :order"
                " LIMIT 1"
            ),
            {
                "wf": workflow,
                "phase_id": _normalize_phase_scope(phase_id),
                "order": order,
            },
        ).fetchone()
    if row is not None:
        raise ValueError(
            f"An approval with order={order} already exists in workflow '{workflow}'"
            f" phase '{phase_id}'"
        )


def _delete_approval_from_db(approval_id: str) -> None:
    """Remove an approval record from the DB."""
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            conn.execute(
                _text("DELETE FROM approval_records WHERE id = :id"),
                {"id": approval_id},
            )
    except Exception as exc:  # pragma: no cover - best effort
        _logger.warning("Failed to delete approval %r from DB: %s", approval_id, exc)


def load_approvals_from_db() -> None:
    """Populate the in-memory ``approvals`` dict from the database.

    Only adds records that are not already present in the cache; existing
    in-memory entries are left unchanged.  Call at startup so the application
    resumes with previously persisted approval state.
    """
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            rows = conn.execute(_text("SELECT data FROM approval_records")).fetchall()
        for (raw,) in rows:
            data = json.loads(raw) if isinstance(raw, str) else raw
            try:
                approval = _approval_from_db_data(data)
                # Only populate cache for records that aren't already loaded
                if approval.id not in approvals:
                    approvals[approval.id] = approval
                    _workflow_approvals.setdefault(
                        _wa_key(approval.workflow, approval.phase_id), []
                    ).append(approval.id)
            except Exception as exc:  # pragma: no cover - skip corrupt rows
                _logger.debug("Skipping corrupt approval row: %s", exc)
    except Exception as exc:  # pragma: no cover - DB not available yet
        _logger.warning("Failed to load approvals from DB: %s", exc)


def reset_approvals() -> None:
    """Clear in-memory approvals and remove all persisted records.

    Scoped to test fixtures.  In production, use targeted deletion instead.
    """
    approvals.clear()
    _approval_locks.clear()
    _workflow_approvals.clear()
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            conn.execute(_text("DELETE FROM approval_records"))
    except Exception as exc:  # pragma: no cover - best effort
        _logger.warning("Failed to clear approval records from DB: %s", exc)


def _hash_document_model(document: DocumentModel) -> str:
    from .signatures import _hash_document_bytes
    return _hash_document_bytes(document.content.encode("utf-8"))


def create_approval(  # noqa: C901
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
    from uuid import uuid4

    from .signatures import _hash_document_bytes

    if doc_id is None:
        doc_id = workflow
    if signature_provider is None:
        signature_provider = get_default_provider()
    approval_id = uuid4().hex

    # B-13: Enforce order uniqueness within the same workflow/phase.
    if order != 0:
        existing = get_approvals_for_workflow(workflow, phase_id)
        if any(a.order == order and a.id != approval_id for a in existing):
            raise ValueError(
                f"An approval with order={order} already exists in workflow '{workflow}'"
                f" phase '{phase_id}'"
            )
        _ensure_unique_order_in_db(workflow, phase_id, order)

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
    # B-08: Maintain secondary index.
    _wa_idx_key = _wa_key(workflow, phase_id)
    _workflow_approvals.setdefault(_wa_idx_key, []).append(approval_id)
    try:
        _persist_approval(approval)
    except ValueError:
        approvals.pop(approval_id, None)
        try:
            _workflow_approvals[_wa_idx_key].remove(approval_id)
        except (KeyError, ValueError):
            pass
        raise
    try:
        link_approval(doc_id, approval_id)
    except KeyError as exc:
        _logger.warning("Failed to link approval %r to document %r: %s", approval_id, doc_id, exc)
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
        try:
            from ..celery_app import app

            app.tasks["docreview360.approval_reminder"].apply_async((approval_id,), eta=reminder_at)
        except Exception as exc:
            _logger.info("Approval reminder scheduling skipped: %s", exc)
    if escalate_to and escalation_at:
        try:
            from ..celery_app import app

            app.tasks["docreview360.approval_escalation"].apply_async(
                (approval_id, escalate_to), eta=escalation_at
            )
        except Exception as exc:
            _logger.info("Approval escalation scheduling skipped: %s", exc)
    return approval


def assign_approval_reviewer(approval_id: str, reviewer: str) -> ApprovalModel:
    """Assign a specific user to an existing approval role.

    Updates the ``reviewer`` field without creating a new approval record.
    Raises :class:`KeyError` if the approval does not exist.
    """
    approval = approvals.get(approval_id)
    if approval is None:
        raise KeyError(f"approval {approval_id!r} not found")
    previous_reviewer = approval.reviewer
    approval.reviewer = reviewer
    _persist_approval(approval)
    log_event(
        "approval_reviewer_assigned",
        approval_id=approval_id,
        workflow=approval.workflow,
        role=approval.role,
        previous_reviewer=previous_reviewer,
        new_reviewer=reviewer,
        doc_id=approval.document_id,
    )
    log_audit_event(
        approval.document_id,
        "reviewer_assigned",
        actor=reviewer,
        approval_id=approval_id,
        workflow=approval.workflow,
        role=approval.role,
        previous_reviewer=previous_reviewer,
    )
    return approval


def get_approval(approval_id: str) -> ApprovalModel | None:
    """Return the approval for *approval_id*, loading from DB if not cached."""
    cached = approvals.get(approval_id)
    if cached is not None:
        return cached
    # Fall back to DB (e.g. after server restart or cache eviction)
    try:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            row = conn.execute(
                _text("SELECT data FROM approval_records WHERE id = :id"),
                {"id": approval_id},
            ).fetchone()
        if row is not None:
            raw = row[0]
            data = json.loads(raw) if isinstance(raw, str) else raw
            approval = _approval_from_db_data(data)
            approvals[approval_id] = approval
            _workflow_approvals.setdefault(
                _wa_key(approval.workflow, approval.phase_id),
                [],
            ).append(approval_id)
            return approval
    except Exception as exc:  # pragma: no cover - DB not available
        _logger.warning("Failed to load approval %r from DB: %s", approval_id, exc)
    return None


def delete_approval(approval_id: str) -> ApprovalModel:
    """Remove an approval and unlink it from its document."""
    approval = approvals.pop(approval_id)
    # B-08: Remove from secondary index.
    _wa_idx_key = _wa_key(approval.workflow, approval.phase_id)
    try:
        _workflow_approvals[_wa_idx_key].remove(approval_id)
    except (KeyError, ValueError):
        pass
    # B-01/B-02: Release the per-approval lock.
    release_approval_lock(approval_id)
    _delete_approval_from_db(approval_id)
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
    from .routing import _reminder_task

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


def approval_dashboard() -> List[Dict[str, Any]]:
    """Return approval data including provider configuration and audit trail."""
    from ..audit import get_audit_log
    from .signatures import _hash_document_model as _hash_doc_model

    data: List[Dict[str, Any]] = []
    for approval in approvals.values():
        current_hash = None
        document = get_document(approval.document_id)
        if document is not None:
            current_hash = _hash_doc_model(document)
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


def reset_approval(
    approval_id: str,
    confirm: bool,
    *,
    username: str,
    password: str,
    otp: str,
    reason: str,
) -> bool:
    from ..auth import authenticate_mfa

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

    if confirm:
        try:
            _do_reset()
        except Exception:
            return False
        return True
    return False
