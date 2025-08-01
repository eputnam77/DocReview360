from pathlib import Path

from cryptography.fernet import Fernet
from docreview360.stubs.task90 import create_backup


def test_create_backup(tmp_path: Path) -> None:
    dest = tmp_path / "backup.txt"
    key = create_backup(dest, "hello")
    data = dest.read_bytes()
    assert Fernet(key).decrypt(data) == b"hello"
