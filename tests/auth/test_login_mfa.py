"""Tests covering MFA enforcement for the login endpoints."""

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


def test_login_without_mfa_required(monkeypatch) -> None:
    """Password-only logins succeed when MFA enforcement is disabled."""

    monkeypatch.setattr(auth, "REQUIRE_MFA", False)
    client = TestClient(app)

    response = client.post(
        "/token",
        data={"username": "alice", "password": "password"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    oidc_response = client.post(
        "/oidc/token",
        data={"username": "alice", "password": "password"},
    )
    assert oidc_response.status_code == 200
    oidc_payload = oidc_response.json()
    assert oidc_payload["token_type"] == "bearer"
    assert oidc_payload["access_token"]


def test_login_with_mfa_required(monkeypatch) -> None:
    """MFA-protected logins reject missing/invalid OTPs and accept valid ones."""

    monkeypatch.setattr(auth, "REQUIRE_MFA", True)
    client = TestClient(app)

    missing_otp = client.post(
        "/token",
        data={"username": "alice", "password": "password"},
    )
    assert missing_otp.status_code == 401

    wrong_otp = client.post(
        "/token",
        data={"username": "alice", "password": "password", "otp": "000000"},
    )
    assert wrong_otp.status_code == 401

    good_otp = client.post(
        "/token",
        data={"username": "alice", "password": "password", "otp": "123456"},
    )
    assert good_otp.status_code == 200

    oidc_missing = client.post(
        "/oidc/token",
        data={"username": "alice", "password": "password"},
    )
    assert oidc_missing.status_code == 401

    oidc_good = client.post(
        "/oidc/token",
        data={"username": "alice", "password": "password", "otp": "123456"},
    )
    assert oidc_good.status_code == 200
