from datetime import datetime, timezone
from pathlib import Path

from docreview360.disaster_recovery import run_disaster_recovery_simulation
from docreview360.documents import DocumentModel, documents
from docreview360.logs import logs
from docreview360.models import LogEntry


def _snapshot_documents() -> dict[str, DocumentModel]:
    return {doc_id: doc.model_copy(deep=True) for doc_id, doc in documents.items()}


def _snapshot_logs() -> list[LogEntry]:
    return [entry.model_copy(deep=True) for entry in logs]


def test_disaster_recovery_simulation_restores_existing_state(tmp_path: Path) -> None:
    original_documents = _snapshot_documents()
    original_logs = _snapshot_logs()

    sentinel_doc = DocumentModel(id="sentinel-doc", content="keep-me")
    sentinel_log = LogEntry(
        id="sentinel-log",
        timestamp=datetime.now(timezone.utc),
        action="sentinel",
    )

    try:
        documents[sentinel_doc.id] = sentinel_doc
        logs.append(sentinel_log)

        result = run_disaster_recovery_simulation(tmp_path / "dr-sim.json.gz")

        assert result.restored_version_count >= 2
        assert result.restored_log_count >= 1
        assert documents.get("sentinel-doc") is not None
        assert any(entry.action == "sentinel" for entry in logs)
    finally:
        documents.clear()
        documents.update(original_documents)
        logs.clear()
        logs.extend(original_logs)
