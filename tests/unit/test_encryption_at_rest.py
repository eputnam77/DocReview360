import base64
import os
from pathlib import Path

import pytest

from docreview360 import backup_utils, crypto
from docreview360.crypto import decrypt_payload, encrypt_payload
from docreview360.secrets import store_secret


def _settings_for_key(key_id: str) -> dict:
    return {
        "security": {
            "encryption_at_rest": {
                "enabled": True,
                "key_id": key_id,
                "required_for": ["backup", "archive"],
            }
        }
    }


def test_encrypt_payload_roundtrip_no_cleartext() -> None:
    key_id = "unit-test-enc-key"
    key = os.urandom(32)
    store_secret(key_id, base64.b64encode(key).decode("ascii"))
    settings = _settings_for_key(key_id)
    plaintext = b"super-secret-data-123"

    encrypted = encrypt_payload(plaintext, settings=settings)

    assert plaintext not in encrypted
    assert b"super-secret" not in encrypted
    assert decrypt_payload(encrypted, settings=settings) == plaintext


def test_restore_backup_missing_key_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_id = "unit-test-backup-key-missing"
    key = os.urandom(32)
    store_secret(key_id, base64.b64encode(key).decode("ascii"))
    settings = _settings_for_key(key_id)
    monkeypatch.setattr(backup_utils, "load_settings", lambda: settings)

    backup_path = tmp_path / "backup.enc"
    backup_utils.create_backup(backup_path)

    monkeypatch.setattr(crypto, "get_secret", lambda _: None)

    with pytest.raises(ValueError, match="backup decryption failed"):
        backup_utils.restore_backup(backup_path)


def test_restore_backup_wrong_key_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_id = "unit-test-backup-key-wrong"
    key = os.urandom(32)
    store_secret(key_id, base64.b64encode(key).decode("ascii"))
    settings = _settings_for_key(key_id)
    monkeypatch.setattr(backup_utils, "load_settings", lambda: settings)

    backup_path = tmp_path / "backup.enc"
    backup_utils.create_backup(backup_path)

    wrong_key = os.urandom(32)
    monkeypatch.setattr(
        crypto,
        "get_secret",
        lambda _: base64.b64encode(wrong_key).decode("ascii"),
    )

    with pytest.raises(ValueError, match="failed to decrypt payload"):
        backup_utils.restore_backup(backup_path)
