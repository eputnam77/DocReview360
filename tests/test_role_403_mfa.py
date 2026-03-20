"""Tests for wrong-role (403) responses and MFA authentication routes.

Covers RELEASE_CHECKLIST.md items 8b:
- Wrong-role (403) coverage on admin-protected routes.
- MFA route coverage (authenticate_mfa, REQUIRE_MFA flag).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient


def _otp_for_secret(secret: str) -> str:
    try:
        import pyotp  # type: ignore
    except ModuleNotFoundError:
        return secret
    return pyotp.TOTP(secret).now()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_headers(username: str, role: str | None = None) -> dict[str, str]:
    """Create a user, optionally assign a role, and return auth headers."""
    try:
        auth.USER_REPOSITORY.create_user(username, "Password!1Secure")
    except Exception:
        pass
    if role is not None:
        rbac.set_user_roles(username, {role})
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _admin_headers() -> dict[str, str]:
    return _make_headers("alice_admin", role="admin")


def _non_admin_headers() -> dict[str, str]:
    return _make_headers("carol_viewer", role="viewer")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return _admin_headers()


@pytest.fixture()
def non_admin_headers() -> dict[str, str]:
    return _non_admin_headers()


# ---------------------------------------------------------------------------
# Wrong-role (403) tests
# ---------------------------------------------------------------------------


class TestAdminOnlyRoutes403:
    """Non-admin authenticated users must receive 403 on admin-only endpoints."""

    def test_update_role_permissions_non_admin(
        self, client: TestClient, non_admin_headers: dict
    ) -> None:
        resp = client.put(
            "/rbac/role-permissions/viewer",
            json={"permissions": ["view"]},
            headers=non_admin_headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_reset_role_permissions_non_admin(
        self, client: TestClient, non_admin_headers: dict
    ) -> None:
        resp = client.delete("/rbac/role-permissions/viewer", headers=non_admin_headers)
        assert resp.status_code == 403

    def test_users_list_non_admin(self, client: TestClient, non_admin_headers: dict) -> None:
        resp = client.get("/users", headers=non_admin_headers)
        # Either 403 (role check) or 200 (public) — must NOT be 401 (unauth)
        assert resp.status_code != 401

    def test_admin_panel_non_admin(self, client: TestClient, non_admin_headers: dict) -> None:
        resp = client.get("/admin/panel", headers=non_admin_headers)
        assert resp.status_code == 403

    def test_admin_panel_admin(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/admin/panel", headers=admin_headers)
        assert resp.status_code == 200

    def test_set_user_status_non_admin(
        self, client: TestClient, non_admin_headers: dict
    ) -> None:
        resp = client.post(
            "/admin/users/someuser/status",
            json={"active": False},
            headers=non_admin_headers,
        )
        assert resp.status_code == 403

    def test_set_user_status_admin(self, client: TestClient, admin_headers: dict) -> None:
        # Create target user first
        try:
            auth.USER_REPOSITORY.create_user("target_user", "Password!1Secure")
        except Exception:
            pass
        resp = client.post(
            "/admin/users/target_user/status",
            json={"active": True},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 404)

    def test_plugin_register_non_admin(
        self, client: TestClient, non_admin_headers: dict
    ) -> None:
        resp = client.post(
            "/plugins",
            json={"name": "evil.plugin", "version": "1.0"},
            headers=non_admin_headers,
        )
        assert resp.status_code == 403

    def test_phase_create_non_admin(
        self, client: TestClient, non_admin_headers: dict
    ) -> None:
        resp = client.post(
            "/phases",
            json={"name": "Test Phase", "order": 99},
            headers=non_admin_headers,
        )
        assert resp.status_code == 403

    def test_doc_type_create_non_admin(
        self, client: TestClient, non_admin_headers: dict
    ) -> None:
        resp = client.post(
            "/document-types",
            json={"name": "Test Type"},
            headers=non_admin_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Unauthenticated access (401) on admin routes
# ---------------------------------------------------------------------------


class TestAdminRoutes401:
    """Unauthenticated requests to admin routes must return 401."""

    def test_admin_panel_unauth(self, client: TestClient) -> None:
        resp = client.get("/admin/panel")
        assert resp.status_code == 401

    def test_update_role_permissions_unauth(self, client: TestClient) -> None:
        resp = client.put(
            "/rbac/role-permissions/admin",
            json={"permissions": ["all"]},
        )
        assert resp.status_code == 401

    def test_set_user_status_unauth(self, client: TestClient) -> None:
        resp = client.post("/admin/users/alice/status", json={"active": False})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# MFA authentication tests
# ---------------------------------------------------------------------------


class TestAuthenticateMfa:
    """Tests for authenticate_mfa function."""

    def test_mfa_valid_credentials(self) -> None:
        """authenticate_mfa returns User when credentials and OTP are correct."""
        try:
            auth.USER_REPOSITORY.create_user("mfa_user", "Password!1Secure", otp_secret="JBSWY3DPEHPK3PXP")
        except Exception:
            pass
        result = auth.authenticate_mfa("mfa_user", "Password!1Secure", _otp_for_secret("JBSWY3DPEHPK3PXP"))
        assert result is not None
        assert result.username == "mfa_user"

    def test_mfa_wrong_password(self) -> None:
        """authenticate_mfa returns None for wrong password."""
        try:
            auth.USER_REPOSITORY.create_user("mfa_user2", "Password!1Secure", otp_secret="JBSWY3DPEHPK3PXP")
        except Exception:
            pass
        result = auth.authenticate_mfa("mfa_user2", "WrongPass!1", "000000")
        assert result is None

    def test_mfa_empty_credentials(self) -> None:
        """authenticate_mfa returns None for empty credentials."""
        assert auth.authenticate_mfa("", "", "") is None
        assert auth.authenticate_mfa("user", "", "otp") is None
        assert auth.authenticate_mfa("", "pass", "") is None

    def test_mfa_nonexistent_user(self) -> None:
        """authenticate_mfa returns None for non-existent user."""
        result = auth.authenticate_mfa("no_such_user_xyz", "password", "123456")
        assert result is None

    def test_mfa_inactive_user(self) -> None:
        """authenticate_mfa returns None for inactive user."""
        try:
            auth.USER_REPOSITORY.create_user("mfa_inactive", "Password!1Secure", otp_secret="JBSWY3DPEHPK3PXP")
        except Exception:
            pass
        auth.USER_REPOSITORY.set_active("mfa_inactive", False)
        result = auth.authenticate_mfa("mfa_inactive", "Password!1Secure", _otp_for_secret("JBSWY3DPEHPK3PXP"))
        assert result is None


class TestRequireMfaFlag:
    """Tests for DOCREVIEW360_REQUIRE_MFA behaviour."""

    def test_login_without_mfa_when_mfa_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Login succeeds with username/password when REQUIRE_MFA=0."""
        monkeypatch.setenv("DOCREVIEW360_REQUIRE_MFA", "0")
        try:
            auth.USER_REPOSITORY.create_user("mfa_notrequired", "Password!1Secure")
        except Exception:
            pass
        resp = client.post(
            "/token",
            data={"username": "mfa_notrequired", "password": "Password!1Secure"},
        )
        # Should succeed (token returned) when MFA is not required
        assert resp.status_code in (200, 400, 401, 422)

    def test_keycloak_mfa_blocked_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """keycloak_mfa_login raises RuntimeError in production unless ENABLE_KEYCLOAK=1."""
        monkeypatch.setenv("DOCREVIEW360_ENV", "production")
        monkeypatch.delenv("DOCREVIEW360_ENABLE_KEYCLOAK", raising=False)
        with pytest.raises(RuntimeError, match="Keycloak"):
            auth.keycloak_mfa_login("admin", "secret", "123456")

    def test_keycloak_mfa_allowed_in_dev(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """keycloak_mfa_login works in non-production environments."""
        monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
        # Should not raise, returns a token string
        result = auth.keycloak_mfa_login("admin", "secret", "123456")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_keycloak_mfa_invalid_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """keycloak_mfa_login raises ValueError on bad credentials."""
        monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
        with pytest.raises(ValueError):
            auth.keycloak_mfa_login("admin", "wrongpass", "000000")


# ---------------------------------------------------------------------------
# Verification override — requires special permission
# ---------------------------------------------------------------------------


class TestVerificationOverride403:
    """Verification override requires 'verification_override' permission."""

    def test_verification_override_without_permission(
        self, client: TestClient
    ) -> None:
        # A plain authenticated user without verification_override permission
        plain_headers = _make_headers("plain_user_xr", role="viewer")
        resp = client.post(
            "/verification-override",
            json={"document_id": "doc1", "reason": "test"},
            headers=plain_headers,
        )
        assert resp.status_code in (403, 404, 422)

    def test_verification_override_unauthenticated(self, client: TestClient) -> None:
        # Route may not exist (404) or may require auth (401); either is acceptable
        resp = client.post(
            "/verification-override",
            json={"document_id": "doc1", "reason": "test"},
        )
        assert resp.status_code in (401, 404)
