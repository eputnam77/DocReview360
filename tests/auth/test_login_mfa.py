"""Tests covering MFA enforcement for the login endpoints."""

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


def _ensure_demo_user() -> tuple[str, str]:
    defaults = auth.DEMO_USER_DEFAULTS["alice"]
    password = defaults["password"]
    otp_secret = defaults["otp_secret"]
    record = auth.USER_REPOSITORY.get_user("alice")
    if record is None or not auth.UserRepository.verify_password(password, record.password_hash):
        auth.USER_REPOSITORY.create_user("alice", password, otp_secret=otp_secret)
        record = auth.USER_REPOSITORY.get_user("alice")
    elif record.otp_secret != otp_secret:
        auth.USER_REPOSITORY.update_otp_secret("alice", otp_secret)
        record = auth.USER_REPOSITORY.get_user("alice")
    if record and not record.active:
        auth.USER_REPOSITORY.set_active("alice", True)
    return password, otp_secret


def test_login_without_mfa_required(monkeypatch) -> None:
    """Password-only logins succeed when MFA enforcement is disabled."""

    monkeypatch.setattr(auth, "REQUIRE_MFA", False)
    password, _ = _ensure_demo_user()
    client = TestClient(app)

    response = client.post(
        "/token",
        data={"username": "alice", "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    oidc_response = client.post(
        "/oidc/token",
        data={"username": "alice", "password": password},
    )
    assert oidc_response.status_code == 200
    oidc_payload = oidc_response.json()
    assert oidc_payload["token_type"] == "bearer"
    assert oidc_payload["access_token"]


def test_login_with_mfa_required(monkeypatch) -> None:
    """MFA-protected logins reject missing/invalid OTPs and accept valid ones."""

    monkeypatch.setattr(auth, "REQUIRE_MFA", True)
    password, otp_secret = _ensure_demo_user()
    client = TestClient(app)

    missing_otp = client.post(
        "/token",
        data={"username": "alice", "password": password},
    )
    assert missing_otp.status_code == 401

    wrong_otp = client.post(
        "/token",
        data={"username": "alice", "password": password, "otp": "000000"},
    )
    assert wrong_otp.status_code == 401

    good_otp = client.post(
        "/token",
        data={"username": "alice", "password": password, "otp": otp_secret},
    )
    assert good_otp.status_code == 200

    oidc_missing = client.post(
        "/oidc/token",
        data={"username": "alice", "password": password},
    )
    assert oidc_missing.status_code == 401

    oidc_good = client.post(
        "/oidc/token",
        data={"username": "alice", "password": password, "otp": otp_secret},
    )
    assert oidc_good.status_code == 200
