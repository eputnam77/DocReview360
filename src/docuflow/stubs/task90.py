"""FedRAMP backup helper providing AES encryption."""

from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet

from . import record_task_completion


def create_backup(path: str | Path, data: str = "", key: bytes | None = None) -> bytes:
    """Write ``data`` encrypted to ``path`` and return the key used."""

    dest = Path(path)
    if not dest.parent.exists():
        raise FileNotFoundError(dest.parent)

    enc_key = key or Fernet.generate_key()
    cipher = Fernet(enc_key)
    token = cipher.encrypt(data.encode())
    dest.write_bytes(token)

    record_task_completion(90)
    return enc_key
