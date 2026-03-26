import hashlib
import json
from pathlib import Path

import docreview360.archive as _archive_mod
import pytest
from docreview360.archive import archive_document, archives
from docreview360.documents import DocumentModel
from docreview360.object_storage import download_file, upload_file


def test_archive_writes_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_archive_mod, "should_encrypt_scope", lambda scope, **kw: False)
    doc = DocumentModel(id="d", content="hello")
    records_before = len(archives)
    record = archive_document(doc, bucket=tmp_path)
    assert len(archives) == records_before + 1
    # verify files exist
    base = tmp_path / f"{doc.id}/{record.id}"
    for ext in [".md", ".html", ".docx", ".pdf", ".metadata.json"]:
        assert (base.with_suffix(ext)).exists()
    metadata = json.loads((base.with_suffix(".metadata.json")).read_text())
    assert metadata["doc_id"] == doc.id
    assert metadata["retention_policy"] == "standard"
    assert metadata["version_summary"] == "v0"
    assert metadata["hashes"]["md"] == hashlib.sha256(record.markdown).hexdigest()


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
    assert isinstance(path, Path)
    assert path.read_bytes() == b"hello"


def test_append_only(tmp_path: Path) -> None:
    upload_file(tmp_path, "bar.txt", b"first", append_only=True)
    with pytest.raises(FileExistsError):
        upload_file(tmp_path, "bar.txt", b"second", append_only=True)
