from pathlib import Path

from docuflow.stubs.task90 import create_backup


def test_create_backup(tmp_path: Path) -> None:
    dest = tmp_path / "backup.txt"
    create_backup(dest)
    assert dest.read_text() == "encrypted backup"
