import base64
import gzip
import json
from datetime import datetime, timezone

import pytest

from docreview360 import backup_utils as bu
from docreview360.documents import DocumentModel, documents
from docreview360.logs import LogEntry, logs


def setup_function(_):
    documents.clear()
    logs.clear()


def test_create_and_restore_backup(tmp_path, monkeypatch):
    monkeypatch.setattr(bu, "enforce_encryption_choice", lambda **kwargs: None)
    doc = DocumentModel(id="1", content="hi")
    documents[doc.id] = doc
    logs.append(LogEntry(id="l1", timestamp=datetime.now(timezone.utc), action="create"))

    backup_path = bu.create_backup(tmp_path / "b.gz", encrypt=False)
    documents.clear()
    logs.clear()
    bu.restore_backup(backup_path)
    assert documents["1"].content == "hi"
    assert logs[0].action == "create"


def test_dump_encodes_yjs(tmp_path, monkeypatch):
    monkeypatch.setattr(bu, "enforce_encryption_choice", lambda **kwargs: None)
    doc = DocumentModel(id="1", content="hi")
    doc.__dict__["yjs_updates"] = [b"abc"]
    documents[doc.id] = doc
    path = bu.create_backup(tmp_path / "b.gz", encrypt=False)
    data = gzip.open(path, "rt", encoding="utf-8")
    with data as fh:
        payload = json.load(fh)
    encoded = payload["documents"][0]["yjs_updates"][0]
    assert encoded == base64.b64encode(b"abc").decode("ascii")


def test_restore_invalid_base64(tmp_path):
    data = {"documents": [{"id": "1", "content": "x", "yjs_updates": ["!"]}], "logs": []}
    p = tmp_path / "bad.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    documents["orig"] = DocumentModel(id="orig", content="y")
    with pytest.raises(ValueError):
        bu.restore_backup(p)
    # State should remain untouched on failure
    assert "orig" in documents


def test_restore_rejects_non_dict_documents(tmp_path):
    """Non-dict entries in the document list should raise an error."""
    data = {"documents": [123], "logs": []}
    p = tmp_path / "bad2.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    documents["orig"] = DocumentModel(id="orig", content="z")
    logs.append(LogEntry(id="l1", timestamp=datetime.now(timezone.utc), action="a"))
    with pytest.raises(ValueError):
        bu.restore_backup(p)
    # Existing state should remain
    assert list(documents.keys()) == ["orig"]
    assert logs and logs[0].id == "l1"
