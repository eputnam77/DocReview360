# SPDX-License-Identifier: MIT
"""Phase-based audit snapshots.

A phase snapshot captures the state of the audit trail at a specific workflow
phase transition.  Snapshots are stored as specialised audit log events so they
inherit the same immutability and integrity guarantees as ordinary entries.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from . import audit as audit_module
from .audit import AuditLogEntry, log_audit_event

SNAPSHOT_EVENT = "phase_snapshot"


def capture_phase_snapshot(
    document_id: str,
    phase: str,
    *,
    actor: str | None = None,
    previous_phase: str | None = None,
    context: dict[str, Any] | None = None,
) -> AuditLogEntry:
    """Record a phase-transition snapshot in the audit log.

    Parameters
    ----------
    document_id:
        Identifier of the document whose phase is advancing.
    phase:
        Name of the phase the document is entering.
    actor:
        Username of the user triggering the transition.
    previous_phase:
        Name of the phase the document is leaving (if known).
    context:
        Additional metadata to attach to the snapshot entry.

    Returns
    -------
    AuditLogEntry
        The persisted snapshot entry.
    """

    extra: dict[str, Any] = {
        "phase": phase,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }
    if previous_phase is not None:
        extra["previous_phase"] = previous_phase
    if context:
        extra.update(context)

    return log_audit_event(
        document_id,
        SNAPSHOT_EVENT,
        actor=actor,
        status="snapshot",
        **extra,
    )


def get_phase_snapshots(document_id: str) -> list[AuditLogEntry]:
    """Return all phase-transition snapshots for ``document_id``.

    Only entries whose ``event`` field equals :data:`SNAPSHOT_EVENT` are
    returned, sorted chronologically.
    """

    audit_log_path = audit_module._AUDIT_LOG_PATH
    if not audit_log_path.exists():
        return []

    snapshots: list[AuditLogEntry] = []
    with audit_log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("document_id") != document_id:
                continue
            if data.get("event") != SNAPSHOT_EVENT:
                continue
            try:
                data["verified_at"] = datetime.fromisoformat(data["verified_at"])
                snapshots.append(AuditLogEntry(**data))
            except Exception:
                continue

    snapshots.sort(key=lambda e: e.verified_at)
    return snapshots
