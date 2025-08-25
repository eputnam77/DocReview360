import datetime as dt
from pathlib import Path

from docreview360.archive import ArchiveRecord, archives, purge_archives


def test_purge_archives_removes_empty_dirs(tmp_path: Path) -> None:
    archives.clear()
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=400)
    doc_id = "doc"
    archive_id = "a1"
    # create dummy file inside bucket/doc_id
    base = tmp_path / doc_id
    base.mkdir()
    (base / f"{archive_id}.txt").write_text("x")
    record = ArchiveRecord(
        id=archive_id,
        document_id=doc_id,
        timestamp=old,
        metadata={},
        markdown=b"",
        html=b"",
        docx=b"",
        pdf=b"",
    )
    archives[archive_id] = record
    removed = purge_archives(retention_days=365, bucket=tmp_path)
    assert removed == 1
    assert archive_id not in archives
    assert not base.exists()
