import base64
import os
from pathlib import Path

import pytest
import yaml
from docreview360 import secrets, settings_manager
from docreview360.crypto import EncryptionKeyError


def _encryption_settings(key_id: str) -> dict:
    return {
        "security": {
            "encryption_at_rest": {
                "enabled": True,
                "key_id": key_id,
                "required_for": ["secrets"],
            }
        }
    }


def _write_settings(path: Path, settings: dict) -> None:
    path.write_text(yaml.safe_dump(settings))


@pytest.fixture(autouse=True)
def clear_vault() -> None:
    secrets._vault._secrets.clear()
    yield
    secrets._vault._secrets.clear()


def test_update_secret_encrypts_and_loads(tmp_path: Path) -> None:
    key_id = "unit-test-secrets-key"
    key = os.urandom(32)
    secrets.store_secret(key_id, base64.b64encode(key).decode("ascii"))
    settings = _encryption_settings(key_id)
    path = tmp_path / "settings.yaml"
    _write_settings(path, settings)

    settings_manager.update_secret("openai", "token-123", path)

    stored = yaml.safe_load(path.read_text())
    assert stored["secrets"]["openai"].startswith(settings_manager.ENCRYPTED_PREFIX)
    loaded = settings_manager.load_settings(path)
    assert loaded["secrets"]["openai"].startswith(settings_manager.ENCRYPTED_PREFIX)
    assert secrets.get_secret("openai") == "token-123"


def test_load_settings_migrates_plaintext_secrets(tmp_path: Path) -> None:
    key_id = "unit-test-legacy-key"
    key = os.urandom(32)
    secrets.store_secret(key_id, base64.b64encode(key).decode("ascii"))
    settings = _encryption_settings(key_id)
    settings["secrets"] = {"openai": "legacy-token"}
    path = tmp_path / "settings.yaml"
    _write_settings(path, settings)

    settings_manager.load_settings(path)

    stored = yaml.safe_load(path.read_text())
    assert stored["secrets"]["openai"].startswith(settings_manager.ENCRYPTED_PREFIX)
    assert secrets.get_secret("openai") == "legacy-token"


def test_update_secret_missing_key_fails(tmp_path: Path) -> None:
    settings = _encryption_settings("missing-key")
    path = tmp_path / "settings.yaml"
    _write_settings(path, settings)

    with pytest.raises(EncryptionKeyError):
        settings_manager.update_secret("openai", "token-123", path)
