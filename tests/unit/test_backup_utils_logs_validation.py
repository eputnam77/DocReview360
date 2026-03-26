import gzip
import json
import os
import tempfile

import pytest
from docreview360.backup_utils import restore_backup


def write_backup(data):
    fd, path = tempfile.mkstemp(suffix=".gz")
    os.close(fd)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def test_restore_backup_rejects_non_dict_logs():
    path = write_backup({"documents": [], "logs": ["not-a-dict"]})
    try:
        with pytest.raises(ValueError):
            restore_backup(path)
    finally:
        os.remove(path)
