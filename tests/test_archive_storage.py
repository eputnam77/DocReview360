from pathlib import Path

import pytest

from docuflow.archive import archive_document, archives
from docuflow.documents import DocumentModel
from docuflow.object_storage import upload_file


def test_archive_writes_files(tmp_path: Path) -> None:
    doc = DocumentModel(id="d", content="hello")
    records_before = len(archives)
    record = archive_document(doc, bucket=tmp_path)
    assert len(archives) == records_before + 1
    # verify files exist
    base = tmp_path / f"{doc.id}/{record.id}"
    for ext in [".md", ".html", ".docx", ".pdf"]:
        assert (base.with_suffix(ext)).exists()


def test_upload_invalid_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        upload_file(tmp_path, "", b"data")
    with pytest.raises(ValueError):
        upload_file(tmp_path, "/bad", b"data")
    with pytest.raises(ValueError):
        upload_file(tmp_path, "bad/", b"data")
