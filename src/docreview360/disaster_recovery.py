"""Disaster recovery simulation for backup and restore validation."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .backup_utils import create_backup, restore_backup
from .documents import DocumentModel, DocumentRevision, documents
from .logs import logs
from .models import LogEntry


@dataclass(frozen=True)
class DisasterRecoverySimulationResult:
    """Summary output for a backup and restore simulation."""

    backup_path: Path
    project_id: str
    document_id: str
    restored_version_count: int
    restored_log_count: int


def _snapshot_documents() -> dict[str, DocumentModel]:
    return {doc_id: doc.model_copy(deep=True) for doc_id, doc in documents.items()}


def _snapshot_logs() -> list[LogEntry]:
    return [entry.model_copy(deep=True) for entry in logs]


def run_disaster_recovery_simulation(
    backup_path: Path | None = None,
) -> DisasterRecoverySimulationResult:
    """Run a backup/restore simulation and validate critical state survival."""

    original_documents = _snapshot_documents()
    original_logs = _snapshot_logs()

    generated_temp = False
    if backup_path is None:
        generated_temp = True
        temp = tempfile.NamedTemporaryFile(
            prefix="docreview360-dr-",
            suffix=".json.gz",
            delete=False,
        )
        backup = Path(temp.name)
        temp.close()
    else:
        backup = Path(backup_path)

    project_id = f"dr-project-{uuid4().hex[:8]}"
    document_id = f"dr-doc-{uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    try:
        documents[document_id] = DocumentModel(
            id=document_id,
            project=project_id,
            content="Version 2",
            history=[
                DocumentRevision(
                    id=f"{document_id}-r1",
                    timestamp=now,
                    content="Version 1",
                    author="dr-sim",
                ),
                DocumentRevision(
                    id=f"{document_id}-r2",
                    timestamp=now,
                    content="Version 2",
                    author="dr-sim",
                ),
            ],
        )
        logs.append(
            LogEntry(
                id=f"dr-log-{uuid4().hex[:8]}",
                timestamp=now,
                user_id="dr-sim",
                action="disaster_recovery.simulation",
                entity_type="project",
                entity_id=project_id,
            )
        )

        create_backup(backup)

        documents.clear()
        logs.clear()
        restore_backup(backup)

        restored_doc = documents.get(document_id)
        if restored_doc is None:
            raise RuntimeError(
                "Disaster recovery simulation failed: document was not restored."
            )
        if restored_doc.project != project_id:
            raise RuntimeError(
                "Disaster recovery simulation failed: project linkage was not restored."
            )
        if len(restored_doc.history) < 2:
            raise RuntimeError(
                "Disaster recovery simulation failed: version history was not restored."
            )
        if not any(
            entry.action == "disaster_recovery.simulation" and entry.entity_id == project_id
            for entry in logs
        ):
            raise RuntimeError(
                "Disaster recovery simulation failed: audit logs were not restored."
            )

        return DisasterRecoverySimulationResult(
            backup_path=backup,
            project_id=project_id,
            document_id=document_id,
            restored_version_count=len(restored_doc.history),
            restored_log_count=len(logs),
        )
    finally:
        documents.clear()
        documents.update(original_documents)
        logs.clear()
        logs.extend(original_logs)
        if generated_temp and backup.exists():
            backup.unlink(missing_ok=True)
