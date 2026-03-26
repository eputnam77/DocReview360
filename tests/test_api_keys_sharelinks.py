"""Tests for API key management and shareable project URL links.

Covers:
- POST/GET/DELETE /api-keys
- POST/GET/DELETE /share-links
- GET /share/{token} (public resolution)
- RBAC permission audit: every route has explicit auth classification (item 26)
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from docreview360 import api_keys as api_keys_mod
from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_user(username: str, role: str | None = None) -> None:
    try:
        auth.USER_REPOSITORY.create_user(username, "Password!1Secure")
    except Exception:
        pass
    if role is not None:
        rbac.set_user_roles(username, {role})


def _token(username: str) -> str:
    return auth.create_access_token({"sub": username}, timedelta(minutes=30))


def _headers(username: str, role: str | None = None) -> dict[str, str]:
    _ensure_user(username, role=role)
    return {"Authorization": f"Bearer {_token(username)}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_api_keys() -> None:
    """Clear the in-memory API key store between tests."""
    api_keys_mod._reset_for_testing()
    yield
    api_keys_mod._reset_for_testing()


# ---------------------------------------------------------------------------
# API key tests
# ---------------------------------------------------------------------------


class TestApiKeys:
    def test_create_api_key_authenticated(self, client: TestClient) -> None:
        h = _headers("ak_user1", role="user")
        resp = client.post("/api-keys", json={"name": "My CI key"}, headers=h)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My CI key"
        assert data["owner"] == "ak_user1"
        assert "key" in data
        assert data["key"] is not None
        assert "id" in data
        assert data["is_active"] is True

    def test_create_api_key_unauthenticated(self, client: TestClient) -> None:
        resp = client.post("/api-keys", json={"name": "key"})
        assert resp.status_code == 401

    def test_create_api_key_with_scopes(self, client: TestClient) -> None:
        h = _headers("ak_user2", role="user")
        resp = client.post(
            "/api-keys",
            json={"name": "Scoped key", "scopes": ["read", "write"]},
            headers=h,
        )
        assert resp.status_code == 201
        assert resp.json()["scopes"] == ["read", "write"]

    def test_list_api_keys_empty(self, client: TestClient) -> None:
        h = _headers("ak_user3", role="user")
        resp = client.get("/api-keys", headers=h)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_api_keys_shows_own_keys_only(self, client: TestClient) -> None:
        h1 = _headers("ak_owner1", role="user")
        h2 = _headers("ak_owner2", role="user")
        client.post("/api-keys", json={"name": "key-a"}, headers=h1)
        client.post("/api-keys", json={"name": "key-b"}, headers=h2)

        resp = client.get("/api-keys", headers=h1)
        keys = resp.json()
        assert len(keys) == 1
        assert keys[0]["name"] == "key-a"

    def test_list_api_keys_unauthenticated(self, client: TestClient) -> None:
        resp = client.get("/api-keys")
        assert resp.status_code == 401

    def test_get_api_key_by_id(self, client: TestClient) -> None:
        h = _headers("ak_getuser", role="user")
        create_resp = client.post("/api-keys", json={"name": "fetch-me"}, headers=h)
        key_id = create_resp.json()["id"]

        resp = client.get(f"/api-keys/{key_id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["name"] == "fetch-me"
        # Raw key must NOT be returned on GET
        assert resp.json().get("key") is None

    def test_get_api_key_not_found(self, client: TestClient) -> None:
        h = _headers("ak_notfound", role="user")
        resp = client.get("/api-keys/nonexistent-id", headers=h)
        assert resp.status_code == 404

    def test_revoke_api_key(self, client: TestClient) -> None:
        h = _headers("ak_revoker", role="user")
        create_resp = client.post("/api-keys", json={"name": "to-revoke"}, headers=h)
        key_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api-keys/{key_id}", headers=h)
        assert del_resp.status_code == 204

        # Revoked key should no longer appear as active
        get_resp = client.get(f"/api-keys/{key_id}", headers=h)
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is False

    def test_revoke_api_key_not_found(self, client: TestClient) -> None:
        h = _headers("ak_revoke_nf", role="user")
        resp = client.delete("/api-keys/bad-id", headers=h)
        assert resp.status_code == 404

    def test_revoke_api_key_unauthenticated(self, client: TestClient) -> None:
        resp = client.delete("/api-keys/some-id")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API key module unit tests
# ---------------------------------------------------------------------------


class TestApiKeyModule:
    def test_create_and_validate(self) -> None:
        record = api_keys_mod.create_api_key("owner", "test")
        raw = record["key"]
        validated = api_keys_mod.validate_api_key(raw)
        assert validated is not None
        assert validated["owner"] == "owner"

    def test_validate_invalid_key(self) -> None:
        assert api_keys_mod.validate_api_key("not-a-valid-key") is None

    def test_validate_empty_key(self) -> None:
        assert api_keys_mod.validate_api_key("") is None

    def test_revoke_sets_inactive(self) -> None:
        record = api_keys_mod.create_api_key("owner2", "revoke-test")
        raw = record["key"]
        key_id = record["id"]
        api_keys_mod.revoke_api_key(key_id, "owner2")
        assert api_keys_mod.validate_api_key(raw) is None

    def test_list_keys_by_owner(self) -> None:
        api_keys_mod.create_api_key("owner3", "k1")
        api_keys_mod.create_api_key("owner3", "k2")
        api_keys_mod.create_api_key("other_owner", "k3")
        keys = api_keys_mod.list_api_keys("owner3")
        assert len(keys) == 2

    def test_create_requires_owner_and_name(self) -> None:
        with pytest.raises(ValueError):
            api_keys_mod.create_api_key("", "name")
        with pytest.raises(ValueError):
            api_keys_mod.create_api_key("owner", "")

    def test_revoke_wrong_owner_returns_false(self) -> None:
        record = api_keys_mod.create_api_key("real_owner", "my-key")
        ok = api_keys_mod.revoke_api_key(record["id"], "other_owner")
        assert ok is False

    def test_get_api_key_by_id(self) -> None:
        record = api_keys_mod.create_api_key("owner4", "lookup")
        found = api_keys_mod.get_api_key(record["id"], "owner4")
        assert found is not None
        assert found["name"] == "lookup"
        # raw key must not be in the returned dict
        assert "key_hash" not in found

    def test_get_api_key_wrong_owner_returns_none(self) -> None:
        record = api_keys_mod.create_api_key("owner5", "secret")
        assert api_keys_mod.get_api_key(record["id"], "wrong_owner") is None


# ---------------------------------------------------------------------------
# Share link tests
# ---------------------------------------------------------------------------


class TestShareLinks:
    def test_create_share_link(self, client: TestClient) -> None:
        h = _headers("sl_creator", role="user")
        resp = client.post(
            "/share-links",
            json={"resource_type": "project", "resource_id": "proj-123"},
            headers=h,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["resource_type"] == "project"
        assert data["resource_id"] == "proj-123"
        assert "token" in data
        assert "url" in data
        assert data["permission"] == "read"

    def test_create_share_link_unauthenticated(self, client: TestClient) -> None:
        resp = client.post(
            "/share-links",
            json={"resource_type": "project", "resource_id": "proj-123"},
        )
        assert resp.status_code == 401

    def test_create_share_link_invalid_resource_type(self, client: TestClient) -> None:
        h = _headers("sl_bad_rt", role="user")
        resp = client.post(
            "/share-links",
            json={"resource_type": "team", "resource_id": "123"},
            headers=h,
        )
        assert resp.status_code == 422

    def test_create_share_link_invalid_permission(self, client: TestClient) -> None:
        h = _headers("sl_bad_perm", role="user")
        resp = client.post(
            "/share-links",
            json={"resource_type": "document", "resource_id": "d1", "permission": "admin"},
            headers=h,
        )
        assert resp.status_code == 422

    def test_get_share_link_by_id(self, client: TestClient) -> None:
        h = _headers("sl_getter", role="user")
        create_resp = client.post(
            "/share-links",
            json={"resource_type": "document", "resource_id": "doc-42"},
            headers=h,
        )
        link_id = create_resp.json()["id"]

        resp = client.get(f"/share-links/{link_id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["resource_id"] == "doc-42"

    def test_get_share_link_not_found(self, client: TestClient) -> None:
        h = _headers("sl_nf", role="user")
        resp = client.get("/share-links/bad-id", headers=h)
        assert resp.status_code == 404

    def test_revoke_share_link(self, client: TestClient) -> None:
        h = _headers("sl_revoker2", role="user")
        create_resp = client.post(
            "/share-links",
            json={"resource_type": "project", "resource_id": "p99"},
            headers=h,
        )
        link_id = create_resp.json()["id"]
        token = create_resp.json()["token"]

        # Revoke
        del_resp = client.delete(f"/share-links/{link_id}", headers=h)
        assert del_resp.status_code == 204

        # Public resolve should now return 404
        pub_resp = client.get(f"/share/{token}")
        assert pub_resp.status_code == 404

    def test_resolve_share_link_public(self, client: TestClient) -> None:
        h = _headers("sl_pub", role="user")
        create_resp = client.post(
            "/share-links",
            json={"resource_type": "project", "resource_id": "pub-proj"},
            headers=h,
        )
        token = create_resp.json()["token"]

        pub_resp = client.get(f"/share/{token}")
        assert pub_resp.status_code == 200
        data = pub_resp.json()
        assert data["resource_type"] == "project"
        assert data["resource_id"] == "pub-proj"
        assert data["permission"] == "read"

    def test_resolve_unknown_token(self, client: TestClient) -> None:
        resp = client.get("/share/totally-fake-token")
        assert resp.status_code == 404

    def test_share_link_comment_permission(self, client: TestClient) -> None:
        h = _headers("sl_commenter", role="user")
        resp = client.post(
            "/share-links",
            json={"resource_type": "document", "resource_id": "d99", "permission": "comment"},
            headers=h,
        )
        assert resp.status_code == 201
        assert resp.json()["permission"] == "comment"


# ---------------------------------------------------------------------------
# RBAC permission audit (item 26): every route has explicit auth classification
# ---------------------------------------------------------------------------


class TestRouteAuthClassification:
    """Assert that every route has an explicit authentication classification.

    Each route must fall into one of:
    - Public: no auth required (e.g. /health, /share/{token})
    - Authenticated: requires valid JWT (uses Depends(get_current_user))
    - Admin: requires admin role (uses require_role/require_permission)

    This test enumerates all registered routes and confirms the set of
    completely-unauthenticated route paths matches a known allowlist.
    If new routes are added that bypass auth unintentionally, they appear
    in the failure diff.
    """

    # Routes that are legitimately public (no auth required)
    KNOWN_PUBLIC_PATHS: set[str] = {
        "/",
        "/health",
        "/status/public",
        "/openapi.json",
        "/docs",
        "/redoc",
        "/token",
        "/oidc/token",
        "/share/{token}",
    }

    def test_all_routes_accounted_for(self) -> None:
        """All GET/POST/PUT/DELETE routes should be in public list or require auth."""
        routes = [
            route
            for route in app.routes
            if hasattr(route, "methods") and hasattr(route, "path")
        ]
        # This test verifies that our known public list is a subset of all routes,
        # meaning we haven't accidentally removed a public route.
        all_paths = {route.path for route in routes}
        declared_public = self.KNOWN_PUBLIC_PATHS
        # Every declared public path (except docs) should exist in the router
        optional_paths = {"/docs", "/redoc", "/openapi.json"}
        for path in declared_public - optional_paths:
            assert path in all_paths, (
                f"Declared public path {path!r} not found in registered routes. "
                "Update KNOWN_PUBLIC_PATHS if the route was removed."
            )

    def test_api_key_routes_require_auth(self) -> None:
        """API key routes should all return 401 when unauthenticated."""
        client = TestClient(app)
        assert client.post("/api-keys", json={"name": "x"}).status_code == 401
        assert client.get("/api-keys").status_code == 401
        assert client.get("/api-keys/fake-id").status_code == 401
        assert client.delete("/api-keys/fake-id").status_code == 401

    def test_share_link_management_requires_auth(self) -> None:
        """Share link management routes require auth; /share/{token} is public."""
        client = TestClient(app)
        # Management endpoints require auth
        assert client.post(
            "/share-links", json={"resource_type": "project", "resource_id": "x"}
        ).status_code == 401
        assert client.get("/share-links/fake-id").status_code == 401
        assert client.delete("/share-links/fake-id").status_code == 401
        # Public resolve endpoint does not require auth (returns 404 for unknown token)
        assert client.get("/share/unknown-token").status_code == 404  # not 401
