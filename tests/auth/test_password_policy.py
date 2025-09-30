import importlib
import sys
from pathlib import Path
from typing import Any

import docreview360
import docreview360.settings_manager as settings_manager
import pytest


def _reload_auth(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop("docreview360.auth", None)
    if hasattr(docreview360, "auth"):
        delattr(docreview360, "auth")
    return importlib.import_module("docreview360.auth")


def test_password_policy_accepts_custom_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_config: dict[str, Any] = {
        "min_length": 6,
        "character_classes": ["lowercase"],
        "min_character_classes": 1,
        "disallow_reuse": False,
    }

    def fake_load_settings(
        path: Path = settings_manager.SETTINGS_FILE,
    ) -> dict[str, Any]:  # pragma: no cover - signature
        return {"auth": {"password_policy": policy_config}}

    monkeypatch.setattr(settings_manager, "load_settings", fake_load_settings)
    db_path = tmp_path / "users.db"
    auth = _reload_auth(monkeypatch, tmp_path, DOCREVIEW360_USER_DB=str(db_path))

    auth.USER_REPOSITORY.create_user("helen", "secretp")
    stored = auth.USER_REPOSITORY.get_user("helen")
    assert stored is not None


def test_password_policy_rejects_short_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "users.db"
    auth = _reload_auth(monkeypatch, tmp_path, DOCREVIEW360_USER_DB=str(db_path))

    with pytest.raises(auth.PasswordPolicyError, match="at least 12 characters"):
        auth.USER_REPOSITORY.create_user("frank", "Short1!")


def test_password_policy_rejects_password_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "users.db"
    auth = _reload_auth(monkeypatch, tmp_path, DOCREVIEW360_USER_DB=str(db_path))

    auth.USER_REPOSITORY.create_user("grace", "Valid-Pass1!")
    with pytest.raises(auth.PasswordPolicyError, match="differ from the previously used"):
        auth.USER_REPOSITORY.create_user("grace", "Valid-Pass1!")


def test_demo_users_not_seeded_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "users.db"
    auth = _reload_auth(
        monkeypatch,
        tmp_path,
        DOCREVIEW360_USER_DB=str(db_path),
        DOCREVIEW360_SEED_DEMO_USERS="false",
    )

    assert auth.USER_REPOSITORY.get_user("alice") is None
    assert auth.USER_REPOSITORY.get_user("bob") is None


def test_demo_users_seeded_with_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "users.db"
    auth = _reload_auth(
        monkeypatch,
        tmp_path,
        DOCREVIEW360_USER_DB=str(db_path),
        DOCREVIEW360_SEED_DEMO_USERS="true",
    )

    alice = auth.USER_REPOSITORY.get_user("alice")
    assert alice is not None
    assert auth.UserRepository.verify_password(
        auth.DEMO_USER_DEFAULTS["alice"]["password"], alice.password_hash
    )

    bob = auth.USER_REPOSITORY.get_user("bob")
    assert bob is not None
    assert auth.UserRepository.verify_password(
        auth.DEMO_USER_DEFAULTS["bob"]["password"], bob.password_hash
    )
