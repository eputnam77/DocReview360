# SPDX-License-Identifier: MIT
"""Core approval CRUD: ApprovalModel, in-memory store, DB persistence."""

from __future__ import annotations

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


def _approval_from_db_data(data: Dict[str, Any]) -> ApprovalModel:
    """Deserialise an :class:`ApprovalModel` from JSON storage."""
    return ApprovalModel.model_validate(data)


def _persist_approval(approval: ApprovalModel) -> None:
    """Upsert *approval* into the ``approval_records`` table."""
    try:
        from sqlalchemy import text as _text

        db = get_db()
        data = _approval_to_db_data(approval)
        with db.session() as conn:
            conn.execute(
                _text(
                    "INSERT INTO approval_records (id, workflow_id, reviewer, state, data)"
                    " VALUES (:id, :wf, :rev, :st, :data)"
                    " ON CONFLICT(id) DO UPDATE SET state=excluded.state, data=excluded.data"
                ),
                {
                    "id": approval.id,
                    "wf": approval.workflow,
                    "rev": approval.reviewer,
                    "st": approval.state,
                    "data": __import__("json").dumps(data),
                },
            )
    except Exception as exc:  # pragma: no cover - best effort
        _logger.warning("Failed to persist approval %r to DB: %s", approval.id, exc)


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
        import json as _json

        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            rows = conn.execute(_text("SELECT data FROM approval_records")).fetchall()
        for (raw,) in rows:
            data = _json.loads(raw) if isinstance(raw, str) else raw
            try:
                approval = _approval_from_db_data(data)
                # Only populate cache for records that aren't already loaded
                if approval.id not in approvals:
                    approvals[approval.id] = approval
            except Exception as exc:  # pragma: no cover - skip corrupt rows
                _logger.debug("Skipping corrupt approval row: %s", exc)
    except Exception as exc:  # pragma: no cover - DB not available yet
        _logger.warning("Failed to load approvals from DB: %s", exc)


def reset_approvals() -> None:
    """Clear in-memory approvals and remove all persisted records.

    Scoped to test fixtures.  In production, use targeted deletion instead.
    """
    approvals.clear()
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
    from uuid import uuid4

    from ..celery_app import app
    from .signatures import _hash_document_bytes

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
    _persist_approval(approval)
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
        app.tasks["docreview360.approval_reminder"].apply_async((approval_id,), eta=reminder_at)
    if escalate_to and escalation_at:
        app.tasks["docreview360.approval_escalation"].apply_async(
            (approval_id, escalate_to), eta=escalation_at
        )
    return approval


def get_approval(approval_id: str) -> ApprovalModel | None:
    """Return the approval for *approval_id*, loading from DB if not cached."""
    cached = approvals.get(approval_id)
    if cached is not None:
        return cached
    # Fall back to DB (e.g. after server restart or cache eviction)
    try:
        import json as _json

        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            row = conn.execute(
                _text("SELECT data FROM approval_records WHERE id = :id"),
                {"id": approval_id},
            ).fetchone()
        if row is not None:
            raw = row[0]
            data = _json.loads(raw) if isinstance(raw, str) else raw
            approval = _approval_from_db_data(data)
            approvals[approval_id] = approval
            return approval
    except Exception as exc:  # pragma: no cover - DB not available
        _logger.warning("Failed to load approval %r from DB: %s", approval_id, exc)
    return None


def delete_approval(approval_id: str) -> ApprovalModel:
    """Remove an approval and unlink it from its document."""
    approval = approvals.pop(approval_id)
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
