from pathlib import Path

from docreview360.backup_utils import create_backup, restore_backup
from docreview360.documents import documents, import_document
from docreview360.logs import clear_logs, log_event, logs


def test_backup_roundtrip(tmp_path: Path) -> None:
    documents.clear()
    clear_logs()
    import_document("a.txt", b"hello")
    log_event("event")

    backup_path = create_backup(tmp_path / "b.gz")
    assert backup_path.exists()

    documents.clear()
    clear_logs()

    restore_backup(backup_path)
    assert documents
    assert any(entry.action == "event" for entry in logs)
