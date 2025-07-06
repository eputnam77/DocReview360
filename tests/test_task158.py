from pathlib import Path

from docuflow.celery_app import create_backup_task, reindex_all
from docuflow.documents import DocumentModel, documents
from docuflow.search import search_index


def test_create_backup_task(tmp_path: Path) -> None:
    dest = tmp_path / "b.gz"
    result = create_backup_task(str(dest))
    assert dest.exists()
    assert result == str(dest)


def test_reindex_all() -> None:
    documents.clear()
    search_index.index.clear()
    doc = DocumentModel(id="1", content="hi", history=[])
    documents["1"] = doc
    count = reindex_all()
    assert count == 1
    assert "1" in {d for ids in search_index.index.values() for d in ids}
