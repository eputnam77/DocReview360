"""Tests for multi-tenant organization CRUD, settings, and API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.db_store import get_db
from docreview360.organizations import (
    OrganizationSettings,
    assign_user_to_org,
    create_organization,
    delete_organization,
    get_org_settings,
    get_organization,
    get_user_org,
    list_org_users,
    list_organizations,
    remove_user_from_org,
    update_org_settings,
    update_organization,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_users(tmp_path: Path) -> Path:
    """Configure auth and rbac to use temporary DBs."""
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    return tmp_path


@pytest.fixture()
def admin_headers(tmp_users: Path) -> dict[str, str]:
    """Return Authorization headers for an admin user (alice)."""
    auth.USER_REPOSITORY.create_user("alice", "Password1!XYZ")
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def regular_headers(tmp_users: Path) -> dict[str, str]:
    """Return Authorization headers for a regular (non-admin) user (bob)."""
    auth.USER_REPOSITORY.create_user("bob", "Password1!XYZ")
    # No admin role for bob
    token = auth.create_access_token({"sub": "bob"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests: organizations.py CRUD
# ---------------------------------------------------------------------------


class TestListOrganizations:
    def test_empty_by_default(self) -> None:
        orgs = list_organizations()
        assert isinstance(orgs, list)

    def test_returns_created_orgs(self) -> None:
        create_organization(name="Acme Corp")
        create_organization(name="Globex")
        orgs = list_organizations()
        names = [o["name"] for o in orgs]
        assert "Acme Corp" in names
        assert "Globex" in names


class TestGetOrganization:
    def test_raises_key_error_for_missing(self) -> None:
        with pytest.raises(KeyError):
            get_organization(org_id=99999)

    def test_returns_correct_org(self) -> None:
        created = create_organization(name="TestOrg")
        fetched = get_organization(org_id=created["id"])
        assert fetched["name"] == "TestOrg"
        assert fetched["id"] == created["id"]


class TestCreateOrganization:
    def test_basic_creation(self) -> None:
        org = create_organization(name="NewOrg")
        assert org["name"] == "NewOrg"
        assert isinstance(org["id"], int)

    def test_creation_with_settings(self) -> None:
        settings = OrganizationSettings(
            max_users=10,
            allowed_doc_types=["SOP", "WI"],
            branding={"color": "#FF0000"},
            custom_phases=["Draft", "Review"],
        )
        org = create_organization(name="SettingsOrg", settings=settings)
        assert org["name"] == "SettingsOrg"
        fetched_settings = get_org_settings(org_id=org["id"])
        assert fetched_settings.max_users == 10
        assert "SOP" in fetched_settings.allowed_doc_types
        assert fetched_settings.branding.get("color") == "#FF0000"

    def test_raises_on_empty_name(self) -> None:
        with pytest.raises(ValueError):
            create_organization(name="")

    def test_raises_on_blank_name(self) -> None:
        with pytest.raises(ValueError):
            create_organization(name="   ")


class TestUpdateOrganization:
    def test_update_name(self) -> None:
        org = create_organization(name="OldName")
        updated = update_organization(org_id=org["id"], name="NewName")
        assert updated["name"] == "NewName"

    def test_update_settings(self) -> None:
        org = create_organization(name="UpdateSettings")
        new_settings = OrganizationSettings(max_users=50)
        updated = update_organization(org_id=org["id"], settings=new_settings)
        fetched_settings = get_org_settings(org_id=org["id"])
        assert fetched_settings.max_users == 50

    def test_no_op_when_nothing_provided(self) -> None:
        org = create_organization(name="NoChange")
        updated = update_organization(org_id=org["id"])
        assert updated["name"] == "NoChange"

    def test_raises_on_missing_org(self) -> None:
        with pytest.raises(KeyError):
            update_organization(org_id=99999, name="X")

    def test_raises_on_empty_name(self) -> None:
        org = create_organization(name="ValidName")
        with pytest.raises(ValueError):
            update_organization(org_id=org["id"], name="")


class TestDeleteOrganization:
    def test_delete_existing(self) -> None:
        org = create_organization(name="ToDelete")
        delete_organization(org_id=org["id"])
        with pytest.raises(KeyError):
            get_organization(org_id=org["id"])

    def test_raises_on_missing(self) -> None:
        with pytest.raises(KeyError):
            delete_organization(org_id=99999)


# ---------------------------------------------------------------------------
# Unit tests: per-org settings
# ---------------------------------------------------------------------------


class TestOrgSettings:
    def test_default_settings(self) -> None:
        org = create_organization(name="DefaultSettings")
        settings = get_org_settings(org_id=org["id"])
        assert isinstance(settings, OrganizationSettings)
        assert settings.max_users == 0
        assert settings.allowed_doc_types == []

    def test_update_and_retrieve_settings(self) -> None:
        org = create_organization(name="SettingsUpdate")
        new_settings = OrganizationSettings(
            max_users=25,
            allowed_doc_types=["Protocol"],
            custom_phases=["Authoring", "QC"],
            branding={"logo": "https://example.com/logo.png"},
        )
        result = update_org_settings(org_id=org["id"], settings=new_settings)
        assert isinstance(result, OrganizationSettings)
        assert result.max_users == 25
        assert "Protocol" in result.allowed_doc_types
        assert "Authoring" in result.custom_phases

    def test_settings_raises_on_missing_org(self) -> None:
        with pytest.raises(KeyError):
            get_org_settings(org_id=99999)

    def test_update_settings_raises_on_missing_org(self) -> None:
        with pytest.raises(KeyError):
            update_org_settings(org_id=99999, settings=OrganizationSettings())


# ---------------------------------------------------------------------------
# Unit tests: user assignment
# ---------------------------------------------------------------------------


def _create_db_user(username: str) -> None:
    """Insert a bare user row into the SQLAlchemy DB used by organizations.py."""
    db = get_db()
    from sqlalchemy import text as _text

    with db.session() as conn:
        conn.execute(
            _text("INSERT OR IGNORE INTO users (username, active) VALUES (:u, 1)"),
            {"u": username},
        )


class TestUserAssignment:
    def test_assign_user_to_org(self) -> None:
        org = create_organization(name="AssignOrg")
        _create_db_user("user1")
        assign_user_to_org(username="user1", org_id=org["id"])
        user_org = get_user_org(username="user1")
        assert user_org is not None
        assert user_org["id"] == org["id"]

    def test_remove_user_from_org(self) -> None:
        org = create_organization(name="RemoveOrg")
        _create_db_user("user2")
        assign_user_to_org(username="user2", org_id=org["id"])
        remove_user_from_org(username="user2")
        assert get_user_org(username="user2") is None

    def test_get_user_org_returns_none_when_unassigned(self) -> None:
        _create_db_user("user3")
        assert get_user_org(username="user3") is None

    def test_assign_raises_on_missing_user(self) -> None:
        org = create_organization(name="NoUserOrg")
        with pytest.raises(KeyError):
            assign_user_to_org(username="nonexistent_user", org_id=org["id"])

    def test_assign_raises_on_missing_org(self) -> None:
        _create_db_user("user4")
        with pytest.raises(KeyError):
            assign_user_to_org(username="user4", org_id=99999)

    def test_remove_raises_on_missing_user(self) -> None:
        with pytest.raises(KeyError):
            remove_user_from_org(username="nobody")

    def test_list_org_users(self) -> None:
        org = create_organization(name="ListUsersOrg")
        _create_db_user("userA")
        _create_db_user("userB")
        assign_user_to_org(username="userA", org_id=org["id"])
        assign_user_to_org(username="userB", org_id=org["id"])
        users = list_org_users(org_id=org["id"])
        usernames = [u["username"] for u in users]
        assert "userA" in usernames
        assert "userB" in usernames

    def test_delete_org_disassociates_users(self) -> None:
        org = create_organization(name="DeleteWithUsers")
        _create_db_user("user5")
        assign_user_to_org(username="user5", org_id=org["id"])
        delete_organization(org_id=org["id"])
        # user5 should have no org now
        assert get_user_org(username="user5") is None


# ---------------------------------------------------------------------------
# API tests: HTTP endpoints
# ---------------------------------------------------------------------------


class TestOrgApiAuth:
    """Verify that unauthenticated requests return 401 and non-admin returns 403."""

    def test_list_orgs_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/organizations")
        assert resp.status_code == 401

    def test_create_org_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/organizations", json={"name": "X"})
        assert resp.status_code == 401

    def test_delete_org_requires_auth(self, client: TestClient) -> None:
        resp = client.delete("/organizations/1")
        assert resp.status_code == 401

    def test_list_orgs_requires_admin(
        self, client: TestClient, regular_headers: dict[str, str]
    ) -> None:
        resp = client.get("/organizations", headers=regular_headers)
        assert resp.status_code == 403

    def test_create_org_requires_admin(
        self, client: TestClient, regular_headers: dict[str, str]
    ) -> None:
        resp = client.post("/organizations", json={"name": "X"}, headers=regular_headers)
        assert resp.status_code == 403

    def test_update_org_requires_admin(
        self, client: TestClient, admin_headers: dict[str, str], regular_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "AdminRequired"}, headers=admin_headers
        )
        assert create_resp.status_code == 201
        org_id = create_resp.json()["id"]
        resp = client.put(
            f"/organizations/{org_id}", json={"name": "New"}, headers=regular_headers
        )
        assert resp.status_code == 403

    def test_delete_org_requires_admin(
        self, client: TestClient, admin_headers: dict[str, str], regular_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "ToDeleteAdmin"}, headers=admin_headers
        )
        assert create_resp.status_code == 201
        org_id = create_resp.json()["id"]
        resp = client.delete(f"/organizations/{org_id}", headers=regular_headers)
        assert resp.status_code == 403

    def test_settings_requires_admin(
        self, client: TestClient, admin_headers: dict[str, str], regular_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "SettingsAdmin"}, headers=admin_headers
        )
        assert create_resp.status_code == 201
        org_id = create_resp.json()["id"]
        resp = client.get(f"/organizations/{org_id}/settings", headers=regular_headers)
        assert resp.status_code == 403


class TestOrgApiCrud:
    """Happy-path CRUD via the HTTP API (admin user)."""

    def test_list_orgs_returns_list(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        resp = client.get("/organizations", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_org(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        resp = client.post(
            "/organizations", json={"name": "API Org"}, headers=admin_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "API Org"
        assert isinstance(data["id"], int)

    def test_create_org_empty_name_returns_400(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        resp = client.post("/organizations", json={"name": ""}, headers=admin_headers)
        assert resp.status_code == 400

    def test_get_org(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "GetOrg"}, headers=admin_headers
        )
        org_id = create_resp.json()["id"]
        resp = client.get(f"/organizations/{org_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetOrg"

    def test_get_org_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        resp = client.get("/organizations/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_update_org_name(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "BeforeUpdate"}, headers=admin_headers
        )
        org_id = create_resp.json()["id"]
        resp = client.put(
            f"/organizations/{org_id}",
            json={"name": "AfterUpdate"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "AfterUpdate"

    def test_update_org_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        resp = client.put(
            "/organizations/99999", json={"name": "X"}, headers=admin_headers
        )
        assert resp.status_code == 404

    def test_delete_org(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "DeleteMe"}, headers=admin_headers
        )
        org_id = create_resp.json()["id"]
        del_resp = client.delete(f"/organizations/{org_id}", headers=admin_headers)
        assert del_resp.status_code == 204
        # Verify it's gone
        get_resp = client.get(f"/organizations/{org_id}", headers=admin_headers)
        assert get_resp.status_code == 404

    def test_delete_org_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        resp = client.delete("/organizations/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestOrgApiSettings:
    """Tests for per-org settings endpoints."""

    def test_get_settings_default(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "DefaultSettingsOrg"}, headers=admin_headers
        )
        org_id = create_resp.json()["id"]
        resp = client.get(f"/organizations/{org_id}/settings", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["max_users"] == 0
        assert data["allowed_doc_types"] == []

    def test_update_settings(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        create_resp = client.post(
            "/organizations", json={"name": "UpdSettingsOrg"}, headers=admin_headers
        )
        org_id = create_resp.json()["id"]
        new_settings = {
            "max_users": 100,
            "allowed_doc_types": ["SOP", "Protocol"],
            "branding": {"primary_color": "#0000FF"},
            "custom_phases": ["Phase1", "Phase2"],
        }
        resp = client.put(
            f"/organizations/{org_id}/settings",
            json=new_settings,
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["max_users"] == 100
        assert "SOP" in data["allowed_doc_types"]
        assert data["branding"].get("primary_color") == "#0000FF"

    def test_settings_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        resp = client.get("/organizations/99999/settings", headers=admin_headers)
        assert resp.status_code == 404


class TestOrgApiUserAssignment:
    """Tests for user assignment endpoints."""

    def test_assign_and_list_users(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        # Create org.
        org_resp = client.post(
            "/organizations", json={"name": "UserAssignOrg"}, headers=admin_headers
        )
        org_id = org_resp.json()["id"]

        # Seed a user into the SQLAlchemy DB.
        _create_db_user("charlie")

        assign_resp = client.post(
            f"/organizations/{org_id}/users/charlie", headers=admin_headers
        )
        assert assign_resp.status_code == 200

        list_resp = client.get(f"/organizations/{org_id}/users", headers=admin_headers)
        assert list_resp.status_code == 200
        usernames = [u["username"] for u in list_resp.json()]
        assert "charlie" in usernames

    def test_remove_user_from_org(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        org_resp = client.post(
            "/organizations", json={"name": "RemoveUserOrg"}, headers=admin_headers
        )
        org_id = org_resp.json()["id"]
        _create_db_user("diana")

        client.post(f"/organizations/{org_id}/users/diana", headers=admin_headers)
        remove_resp = client.delete(
            f"/organizations/{org_id}/users/diana", headers=admin_headers
        )
        assert remove_resp.status_code == 200

        list_resp = client.get(f"/organizations/{org_id}/users", headers=admin_headers)
        usernames = [u["username"] for u in list_resp.json()]
        assert "diana" not in usernames

    def test_assign_missing_user_returns_404(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        org_resp = client.post(
            "/organizations", json={"name": "MissingUserOrg"}, headers=admin_headers
        )
        org_id = org_resp.json()["id"]
        resp = client.post(
            f"/organizations/{org_id}/users/ghost_user", headers=admin_headers
        )
        assert resp.status_code == 404

    def test_assign_missing_org_returns_404(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        _create_db_user("earl")
        resp = client.post(
            "/organizations/99999/users/earl", headers=admin_headers
        )
        assert resp.status_code == 404

    def test_list_org_users_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/organizations/1/users")
        assert resp.status_code == 401

    def test_assign_user_requires_admin(
        self, client: TestClient, regular_headers: dict[str, str], admin_headers: dict[str, str]
    ) -> None:
        org_resp = client.post(
            "/organizations", json={"name": "AssignAdminOnly"}, headers=admin_headers
        )
        org_id = org_resp.json()["id"]
        _create_db_user("frank")
        resp = client.post(
            f"/organizations/{org_id}/users/frank", headers=regular_headers
        )
        assert resp.status_code == 403
