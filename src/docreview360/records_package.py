# SPDX-License-Identifier: MIT
"""Review record package generator — assembles the complete review record for NARA submission
(Item 44 Phase 7)."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RecordsManifest(BaseModel):
    """Complete manifest of a project's review record package."""

    project_id: str
    project_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    lifecycle_status: str
    assignments: list[dict[str, Any]] = Field(default_factory=list)
    feedback_items: list[dict[str, Any]] = Field(default_factory=list)
    notification_log: list[dict[str, Any]] = Field(default_factory=list)
    nara_metadata: dict[str, Any] = Field(default_factory=dict)
    document_versions: list[dict[str, Any]] = Field(default_factory=list)
    audit_entries: int = 0
    integrity_hash: str = ""


# ---------------------------------------------------------------------------
# Package generation
# ---------------------------------------------------------------------------


def generate_records_package(project_id: str) -> tuple[RecordsManifest, bytes]:
    """Assemble the complete review record package for a project.

    Returns (manifest, zip_bytes).  The ZIP contains:
    - manifest.json   — structured manifest (machine-readable)
    - assignments.json
    - feedback.json
    - notifications.json
    - nara_metadata.json
    - document_versions.json
    """
    # ── Collect data ────────────────────────────────────────────────────────
    assignments = _collect_assignments(project_id)
    feedback = _collect_feedback(project_id)
    notifications = _collect_notifications(project_id)
    nara_meta = _collect_nara_metadata(project_id)
    doc_versions = _collect_document_versions(project_id)
    lifecycle_status = _get_lifecycle_status(project_id)
    project_name = _get_project_name(project_id)

    manifest = RecordsManifest(
        project_id=project_id,
        project_name=project_name,
        lifecycle_status=lifecycle_status,
        assignments=assignments,
        feedback_items=feedback,
        notification_log=notifications,
        nara_metadata=nara_meta,
        document_versions=doc_versions,
    )

    # ── Build ZIP ───────────────────────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        _write_json(zf, "assignments.json", assignments)
        _write_json(zf, "feedback.json", feedback)
        _write_json(zf, "notifications.json", notifications)
        _write_json(zf, "nara_metadata.json", nara_meta)
        _write_json(zf, "document_versions.json", doc_versions)
        # Write manifest last (after computing hash of everything else)
        manifest_dict = manifest.model_dump(mode="json")
        manifest_dict["integrity_hash"] = ""  # placeholder
        zf.writestr("manifest.json", json.dumps(manifest_dict, indent=2))

    zip_bytes = buf.getvalue()
    integrity_hash = hashlib.sha256(zip_bytes).hexdigest()

    # Re-build ZIP with real hash in manifest
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        _write_json(zf, "assignments.json", assignments)
        _write_json(zf, "feedback.json", feedback)
        _write_json(zf, "notifications.json", notifications)
        _write_json(zf, "nara_metadata.json", nara_meta)
        _write_json(zf, "document_versions.json", doc_versions)
        manifest.integrity_hash = integrity_hash
        zf.writestr("manifest.json", json.dumps(manifest.model_dump(mode="json"), indent=2))

    final_bytes = buf2.getvalue()
    # Recompute hash of final ZIP
    manifest.integrity_hash = hashlib.sha256(final_bytes).hexdigest()

    return manifest, final_bytes


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _write_json(zf: zipfile.ZipFile, name: str, data: Any) -> None:
    zf.writestr(name, json.dumps(data, indent=2, default=str))


def _get_lifecycle_status(project_id: str) -> str:
    try:
        from .project_lifecycle import get_lifecycle
        return get_lifecycle(project_id).status
    except Exception:
        return "unknown"


def _get_project_name(project_id: str) -> str:
    try:
        from .search import get_project
        p = get_project(project_id)
        return p.name if p else project_id
    except Exception:
        return project_id


def _collect_assignments(project_id: str) -> list[dict[str, Any]]:
    try:
        from .review_assignments import list_assignments
        return [a.model_dump(mode="json") for a in list_assignments(project_id)]
    except Exception as exc:
        _logger.debug("records_package: assignments failed: %s", exc)
        return []


def _collect_feedback(project_id: str) -> list[dict[str, Any]]:
    try:
        from .feedback_ledger import list_feedback_items
        return [f.model_dump(mode="json") for f in list_feedback_items(project_id)]
    except Exception as exc:
        _logger.debug("records_package: feedback failed: %s", exc)
        return []


def _collect_notifications(project_id: str) -> list[dict[str, Any]]:
    try:
        from .notification_log import list_notification_log
        return [e.model_dump(mode="json") for e in list_notification_log(project_id, limit=500)]
    except Exception as exc:
        _logger.debug("records_package: notifications failed: %s", exc)
        return []


def _collect_nara_metadata(project_id: str) -> dict[str, Any]:
    """Collect NARA metadata for all documents in the project."""
    try:
        from .db_store import get_db
        from sqlalchemy import text as _text
        db = get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text(
                    "SELECT d.id FROM documents d WHERE d.project = :pid"
                ),
                {"pid": project_id},
            ).fetchall()
        if not rows:
            return {}
        from .nara_metadata import get_nara_metadata
        result: dict[str, Any] = {}
        with get_db().session() as session:  # type: ignore[assignment]
            for (doc_id,) in rows:
                meta = get_nara_metadata(session, doc_id)  # type: ignore[arg-type]
                if meta:
                    result[doc_id] = {
                        "schedule_number": meta.schedule_number,
                        "disposition_authority": meta.disposition_authority,
                        "retention_period": meta.retention_period,
                        "record_series_title": meta.record_series_title,
                        "record_status": meta.record_status,
                        "vital_record": meta.vital_record,
                        "classified": meta.classified,
                    }
        return result
    except Exception as exc:
        _logger.debug("records_package: NARA metadata failed: %s", exc)
        return {}


def _collect_document_versions(project_id: str) -> list[dict[str, Any]]:
    """Collect document version history for the project."""
    try:
        from .db_store import get_db
        from sqlalchemy import text as _text
        db = get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text(
                    "SELECT id, version_number, frozen, created_at, author "
                    "FROM documents WHERE project = :pid "
                    "ORDER BY created_at"
                ),
                {"pid": project_id},
            ).fetchall()
        return [
            {
                "id": r[0],
                "version_number": r[1],
                "frozen": bool(r[2]),
                "created_at": r[3],
                "author": r[4],
            }
            for r in rows
        ]
    except Exception as exc:
        _logger.debug("records_package: document versions failed: %s", exc)
        return []
