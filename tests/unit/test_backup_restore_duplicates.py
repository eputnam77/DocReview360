import gzip
import json

import pytest
from docreview360.backup_utils import restore_backup


def test_restore_backup_duplicate_documents(tmp_path):
    doc = {"id": "dup", "content": "a"}
    backup = {"documents": [doc, doc], "logs": []}
    path = tmp_path / "dup.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(backup, fh)

    with pytest.raises(ValueError):
        restore_backup(path)
