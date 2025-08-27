import base64
import gzip
import json
from pathlib import Path

import pytest

from docreview360 import backup_utils as bu
from docreview360.documents import DocumentModel, documents
from datetime import datetime, timezone

from docreview360.logs import LogEntry, logs


def setup_function(_):
    documents.clear()
    logs.clear()


def test_create_and_restore_backup(tmp_path):
    doc = DocumentModel(id="1", content="hi")
    documents[doc.id] = doc
    logs.append(LogEntry(id="l1", timestamp=datetime.now(timezone.utc), action="create"))

    backup_path = bu.create_backup(tmp_path / "b.gz")
    documents.clear()
    logs.clear()
    bu.restore_backup(backup_path)
    assert documents["1"].content == "hi"
    assert logs[0].action == "create"


def test_restore_invalid_base64(tmp_path):
    data = {"documents": [{"id": "1", "content": "x", "yjs_updates": ["!"]}], "logs": []}
    p = tmp_path / "bad.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    with pytest.raises(ValueError):
        bu.restore_backup(p)
