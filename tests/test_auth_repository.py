import importlib
import sys
from datetime import datetime, timezone

import docreview360
import pyotp


def _reload_auth(monkeypatch, tmp_path, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop("docreview360.auth", None)
    if hasattr(docreview360, "auth"):
        delattr(docreview360, "auth")
    return importlib.import_module("docreview360.auth")


def test_hashed_credentials_authenticate(tmp_path, monkeypatch):
    db_path = tmp_path / "users.db"
    auth = _reload_auth(monkeypatch, tmp_path, DOCREVIEW360_USER_DB=str(db_path))
    secret = pyotp.random_base32()
    auth.USER_REPOSITORY.create_user("carol", "S3cr3t-Pass!", otp_secret=secret)

    user = auth.authenticate_user("carol", "S3cr3t-Pass!")

    assert user is not None
    assert user.username == "carol"
    stored = auth.USER_REPOSITORY.get_user("carol")
    assert stored is not None
    assert stored.password_hash != "s3cr3t-pass"


def test_invalid_password_triggers_lockout(tmp_path, monkeypatch):
    db_path = tmp_path / "users.db"
    auth = _reload_auth(
        monkeypatch,
        tmp_path,
        DOCREVIEW360_USER_DB=str(db_path),
        DOCREVIEW360_MAX_FAILED_ATTEMPTS="2",
        DOCREVIEW360_LOCKOUT_SECONDS="600",
    )
    auth.USER_REPOSITORY.create_user("dave", "Correct-Horse3!")

    assert auth.authenticate_user("dave", "wrong") is None
    assert auth.authenticate_user("dave", "wrong-again") is None

    locked_record = auth.USER_REPOSITORY.get_user("dave")
    assert locked_record is not None and locked_record.locked_until is not None
    assert locked_record.locked_until > datetime.now(timezone.utc)

    # Locked users cannot authenticate even with the correct password.
    assert auth.authenticate_user("dave", "Correct-Horse3!") is None


def test_invalid_otp_is_rejected(tmp_path, monkeypatch):
    db_path = tmp_path / "users.db"
    auth = _reload_auth(monkeypatch, tmp_path, DOCREVIEW360_USER_DB=str(db_path))
    secret = pyotp.random_base32()
    auth.USER_REPOSITORY.create_user("erin", "Otp-Pass456!", otp_secret=secret)

    assert auth.authenticate_mfa("erin", "Otp-Pass456!", "000000") is None

    valid = pyotp.TOTP(secret).now()
    assert auth.authenticate_mfa("erin", "Otp-Pass456!", valid) is not None


def test_environment_toggle_controls_mfa(tmp_path, monkeypatch):
    db_path = tmp_path / "users.db"
    auth_enabled = _reload_auth(
        monkeypatch,
        tmp_path,
        DOCREVIEW360_USER_DB=str(db_path),
        DOCREVIEW360_REQUIRE_MFA="true",
    )
    assert auth_enabled.REQUIRE_MFA is True

    auth_disabled = _reload_auth(
        monkeypatch,
        tmp_path,
        DOCREVIEW360_USER_DB=str(db_path),
        DOCREVIEW360_REQUIRE_MFA="false",
    )
    assert auth_disabled.REQUIRE_MFA is False
