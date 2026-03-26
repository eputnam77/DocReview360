import gzip
import json
from datetime import datetime, timezone

import pytest
from docreview360.backup_utils import restore_backup
from docreview360.documents import DocumentModel, documents
from docreview360.logs import LogEntry, logs


def test_restore_backup_invalid_data_does_not_wipe_state(tmp_path):
    """A failing restore should not clear existing documents or logs."""

    # Set up some existing in-memory state that must survive the failed restore
    documents.clear()
    logs.clear()
    doc = DocumentModel(id="orig", content="hello")
    documents[doc.id] = doc
    entry = LogEntry(id="1", timestamp=datetime.now(timezone.utc), action="a")
    logs.append(entry)

    # Craft a backup with invalid base64 in ``yjs_updates`` to trigger failure
    bad = {
        "documents": [{"id": "bad", "content": "x", "yjs_updates": ["!!notb64!!"]}],
        "logs": [],
    }
    path = tmp_path / "bad.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(bad, fh)

    with pytest.raises(ValueError):
        restore_backup(path)

    # Original state must remain intact
    assert documents == {doc.id: doc}
    assert logs == [entry]
