import gzip

import pytest
from docreview360.backup_utils import restore_backup


def test_restore_backup_invalid_utf8(tmp_path):
    path = tmp_path / "bad.gz"
    with gzip.open(path, "wb") as fh:
        fh.write(b"\x80\x81")
    with pytest.raises(ValueError):
        restore_backup(path)
