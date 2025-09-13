from pathlib import Path

import pytest

from docreview360.backup_utils import restore_backup


def test_restore_backup_invalid_gzip(tmp_path: Path) -> None:
    path = tmp_path / "bad.gz"
    # Write plain text so gzip will fail during decompression
    path.write_text("not a gzip")
    with pytest.raises(ValueError):
        restore_backup(path)
