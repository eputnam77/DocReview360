# SPDX-License-Identifier: MIT
"""Tests for keycloak_auth — Keycloak claim extraction and role mapping."""

from __future__ import annotations

import json

import pytest

from docreview360 import keycloak_auth


# ---------------------------------------------------------------------------
# extract_keycloak_roles
# ---------------------------------------------------------------------------


def test_extract_realm_roles_only():
    claims = {
        "realm_access": {"roles": ["offline_access", "docreview-admin"]},
    }
    roles = keycloak_auth.extract_keycloak_roles(claims)
    assert "offline_access" in roles
    assert "docreview-admin" in roles


def test_extract_resource_access_roles_only(monkeypatch):
    monkeypatch.setenv("OIDC_CLIENT_ID", "docreview360")
    monkeypatch.delenv("KEYCLOAK_CLIENT_ID_FOR_ROLES", raising=False)
    claims = {
        "resource_access": {
            "docreview360": {"roles": ["docreview-reviewer"]},
        },
    }
    roles = keycloak_auth.extract_keycloak_roles(claims)
    assert roles == ["docreview-reviewer"]


def test_extract_both_realm_and_resource_roles(monkeypatch):
    monkeypatch.setenv("OIDC_CLIENT_ID", "docreview360")
    monkeypatch.delenv("KEYCLOAK_CLIENT_ID_FOR_ROLES", raising=False)
    claims = {
        "realm_access": {"roles": ["default-roles-myrealm", "admin-realm"]},
        "resource_access": {
            "docreview360": {"roles": ["docreview-reviewer", "admin-realm"]},
        },
    }
    roles = keycloak_auth.extract_keycloak_roles(claims)
    # Deduplication: "admin-realm" appears only once
    assert roles.count("admin-realm") == 1
    assert "default-roles-myrealm" in roles
    assert "docreview-reviewer" in roles


def test_extract_empty_claims():
    roles = keycloak_auth.extract_keycloak_roles({})
    assert roles == []


def test_extract_missing_roles_key():
    claims = {
        "realm_access": {},  # no "roles" key inside
    }
    roles = keycloak_auth.extract_keycloak_roles(claims)
    assert roles == []


def test_extract_custom_realm_claim(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_REALM_ROLES_CLAIM", "custom_realm")
    claims = {
        "custom_realm": {"roles": ["special-role"]},
        "realm_access": {"roles": ["should-not-appear"]},
    }
    roles = keycloak_auth.extract_keycloak_roles(claims)
    assert "special-role" in roles
    assert "should-not-appear" not in roles


def test_extract_uses_keycloak_client_id_for_roles_env(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID_FOR_ROLES", "my-special-client")
    monkeypatch.setenv("OIDC_CLIENT_ID", "other-client")
    claims = {
        "resource_access": {
            "my-special-client": {"roles": ["special-role"]},
            "other-client": {"roles": ["should-not-appear"]},
        },
    }
    roles = keycloak_auth.extract_keycloak_roles(claims)
    assert "special-role" in roles
    assert "should-not-appear" not in roles


def test_extract_ignores_non_string_roles():
    claims = {
        "realm_access": {"roles": ["valid-role", 42, None, "another-role"]},
    }
    roles = keycloak_auth.extract_keycloak_roles(claims)
    assert roles == ["valid-role", "another-role"]


# ---------------------------------------------------------------------------
# map_keycloak_roles_to_docreview
# ---------------------------------------------------------------------------


def test_map_with_matching_roles(monkeypatch):
    role_map = {"docreview-admin": "admin", "docreview-reviewer": "reviewer"}
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", json.dumps(role_map))
    result = keycloak_auth.map_keycloak_roles_to_docreview(
        ["docreview-admin", "docreview-reviewer"]
    )
    assert result == ["admin", "reviewer"]


def test_map_with_no_matching_roles_returns_default(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", json.dumps({}))
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "viewer")
    result = keycloak_auth.map_keycloak_roles_to_docreview(["offline_access"])
    assert result == ["viewer"]


def test_map_unmapped_roles_are_dropped(monkeypatch):
    role_map = {"docreview-admin": "admin"}
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", json.dumps(role_map))
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "reviewer")
    # "offline_access" is not in map, so it is dropped; "docreview-admin" maps to "admin"
    result = keycloak_auth.map_keycloak_roles_to_docreview(
        ["offline_access", "docreview-admin"]
    )
    assert result == ["admin"]


def test_map_empty_input_returns_default(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", "{}")
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "reviewer")
    result = keycloak_auth.map_keycloak_roles_to_docreview([])
    assert result == ["reviewer"]


def test_map_deduplicates_output(monkeypatch):
    role_map = {"role-a": "admin", "role-b": "admin"}
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", json.dumps(role_map))
    result = keycloak_auth.map_keycloak_roles_to_docreview(["role-a", "role-b"])
    assert result == ["admin"]


def test_map_default_role_env_default(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_DEFAULT_ROLE", raising=False)
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", "{}")
    result = keycloak_auth.map_keycloak_roles_to_docreview([])
    assert result == ["reviewer"]


# ---------------------------------------------------------------------------
# get_user_info_from_keycloak_claims
# ---------------------------------------------------------------------------


def test_get_user_info_full_claims(monkeypatch):
    role_map = {"docreview-admin": "admin"}
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", json.dumps(role_map))
    monkeypatch.setenv("OIDC_CLIENT_ID", "docreview360")
    monkeypatch.delenv("KEYCLOAK_CLIENT_ID_FOR_ROLES", raising=False)
    claims = {
        "preferred_username": "jdoe",
        "email": "jdoe@example.com",
        "given_name": "John",
        "family_name": "Doe",
        "name": "John Doe",
        "realm_access": {"roles": ["docreview-admin"]},
    }
    info = keycloak_auth.get_user_info_from_keycloak_claims(claims)
    assert info["username"] == "jdoe"
    assert info["email"] == "jdoe@example.com"
    assert info["full_name"] == "John Doe"
    assert "admin" in info["roles"]


def test_get_user_info_falls_back_to_email_for_username(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", "{}")
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "reviewer")
    claims = {
        "email": "fallback@example.com",
        "sub": "abc-123",
    }
    info = keycloak_auth.get_user_info_from_keycloak_claims(claims)
    assert info["username"] == "fallback@example.com"


def test_get_user_info_falls_back_to_sub_for_username(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", "{}")
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "reviewer")
    claims = {"sub": "uuid-sub-value"}
    info = keycloak_auth.get_user_info_from_keycloak_claims(claims)
    assert info["username"] == "uuid-sub-value"


def test_get_user_info_constructs_full_name_from_parts(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", "{}")
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "reviewer")
    claims = {
        "preferred_username": "jsmith",
        "given_name": "Jane",
        "family_name": "Smith",
    }
    info = keycloak_auth.get_user_info_from_keycloak_claims(claims)
    assert info["full_name"] == "Jane Smith"


def test_get_user_info_empty_email_when_absent(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", "{}")
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "reviewer")
    claims = {"preferred_username": "nomail"}
    info = keycloak_auth.get_user_info_from_keycloak_claims(claims)
    assert info["email"] == ""


def test_get_user_info_default_role_when_no_mapping(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ROLE_MAP", "{}")
    monkeypatch.setenv("KEYCLOAK_DEFAULT_ROLE", "auditor")
    claims = {
        "preferred_username": "anon",
        "realm_access": {"roles": ["some-unmapped-role"]},
    }
    info = keycloak_auth.get_user_info_from_keycloak_claims(claims)
    assert info["roles"] == ["auditor"]


# ---------------------------------------------------------------------------
# is_keycloak_provider
# ---------------------------------------------------------------------------


def test_is_keycloak_provider_with_keycloak_in_url():
    assert keycloak_auth.is_keycloak_provider("https://keycloak.example.com/auth") is True


def test_is_keycloak_provider_with_realms_path():
    assert keycloak_auth.is_keycloak_provider(
        "https://sso.example.com/realms/myrealm"
    ) is True


def test_is_keycloak_provider_keycloak_case_insensitive():
    assert keycloak_auth.is_keycloak_provider("https://KEYCLOAK.internal/auth") is True


def test_is_keycloak_provider_with_auth0():
    assert keycloak_auth.is_keycloak_provider("https://myapp.auth0.com") is False


def test_is_keycloak_provider_with_azure_ad():
    assert (
        keycloak_auth.is_keycloak_provider(
            "https://login.microsoftonline.com/tenant-id/v2.0"
        )
        is False
    )


def test_is_keycloak_provider_with_okta():
    assert keycloak_auth.is_keycloak_provider("https://dev-123.okta.com") is False


def test_is_keycloak_provider_empty_string():
    assert keycloak_auth.is_keycloak_provider("") is False
