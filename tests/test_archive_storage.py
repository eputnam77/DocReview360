from pathlib import Path

import pytest
from docreview360.archive import archive_document, archives
from docreview360.documents import DocumentModel
from docreview360.object_storage import download_file, upload_file


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


def test_download_roundtrip(tmp_path: Path) -> None:
    path = upload_file(tmp_path, "foo.txt", b"hello")
    assert download_file(tmp_path, "foo.txt") == b"hello"
    assert path.read_bytes() == b"hello"
