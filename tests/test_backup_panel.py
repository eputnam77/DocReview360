from pathlib import Path

from docuflow.backup_panel import create_backup_async, schedule_daily_backup
from docuflow.celery_app import app
from docuflow.documents import documents, import_document
from docuflow.logs import log_event, logs


def test_create_backup_async(tmp_path: Path) -> None:
    documents.clear()
    logs.clear()
    import_document("a.txt", b"hi")
    log_event("e")
    path = tmp_path / "b.gz"
    result = create_backup_async(str(path))
    assert Path(result).exists()


def test_schedule_daily_backup(tmp_path: Path) -> None:
    schedule_daily_backup(str(tmp_path / "daily.gz"))
    entry = app.conf.beat_schedule["daily_backup"]
    assert entry["args"][0] == str(tmp_path / "daily.gz")
