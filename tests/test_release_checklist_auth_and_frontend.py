from __future__ import annotations

import importlib
import json
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from docreview360 import auth, db_store, jit_provisioning, ldap_auth, oidc_client, rbac, sod
from docreview360.api import app
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[1]
auth_router_module = importlib.import_module("docreview360.api.auth_router")
saml_router_module = importlib.import_module("docreview360.api.saml_router")


def _project_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _ensure_user(username: str, password: str = "Strong-Pass123!") -> None:
    repo = auth._get_user_repository()
    if repo.get_user(username) is None:
        repo.create_user(username, password)


def _bearer_headers(username: str) -> dict[str, str]:
    _ensure_user(username)
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _scim_headers() -> dict[str, str]:
    return {"Authorization": "Bearer scim-secret"}


@pytest.fixture(autouse=True)
def _isolated_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    user_db = tmp_path / "users.db"
    roles_db = tmp_path / "roles.db"
    app_db = tmp_path / "docreview360.db"

    monkeypatch.setenv("DOCREVIEW360_USER_DB", str(user_db))
    monkeypatch.setenv("DOCREVIEW360_RBAC_DB", str(roles_db))
    auth.configure_user_repository(user_db)
    rbac.configure_role_repository(roles_db)
    rbac.reset_role_assignments(include_defaults=False)
    db_store.reset_db(f"sqlite:///{app_db}")
    yield
    db_store.reset_db(None)


def test_filelock_dependency_removed_from_runtime_metadata() -> None:
    assert "filelock" not in _project_file("requirements.txt")
    assert "filelock" not in _project_file("src/docreview360.egg-info/PKG-INFO")
    assert "filelock" not in _project_file("src/docreview360.egg-info/requires.txt")


def test_license_report_labels_docreview360_as_mit() -> None:
    report = _project_file("docs/licenses-report.md")
    docreview_rows = [line for line in report.splitlines() if "| docreview360 " in line]
    assert docreview_rows
    assert all("| MIT " in line for line in docreview_rows)
    assert not any("GPL" in line for line in docreview_rows)


def test_project_pages_use_shared_react_query_hooks() -> None:
    projects_index = _project_file("frontend/pages/projects/index.tsx")
    dashboard = _project_file("frontend/pages/dashboard/index.tsx")
    new_project = _project_file("frontend/pages/projects/new.tsx")

    assert "useProjects" in projects_index
    assert 'authenticatedFetch(endpoint)' not in projects_index
    assert "useProjects" in dashboard
    assert 'authenticatedFetch("/projects")' not in dashboard
    assert "useCreateProject" in new_project
    assert 'authenticatedFetch(`${API}/projects`' not in new_project


def test_translation_hook_has_public_locale_fallback_for_logged_out_pages() -> None:
    hook_source = _project_file("frontend/lib/useTranslation.ts")
    assert "/locales/" in hook_source
    assert "common.json" in hook_source
    assert "_loadPublicLocaleStrings" in hook_source


def test_admin_dashboard_reads_audit_feed_and_uses_permissions_copy() -> None:
    admin_dashboard = _project_file("frontend/pages/dashboard/admin.tsx")
    assert "/api/audit" in admin_dashboard
    assert "permissions" in admin_dashboard
    assert "perms" not in admin_dashboard


def test_project_approval_picker_accepts_invited_reviewers() -> None:
    project_page = _project_file("frontend/pages/projects/[id]/index.tsx")
    assert "approvalReviewerOptions" in project_page
    assert "Invite the reviewer in the Reviewers section before adding a phase approval." in project_page


def test_checker_uses_public_documents_fallback_and_descriptive_labels() -> None:
    checker_page = _project_file("frontend/pages/tools/checker.tsx")
    assert "/documents/public" in checker_page
    assert "Showing public system documents only." in checker_page
    assert "formatSystemDocumentLabel" in checker_page


def test_revoked_tokens_are_persisted_in_auth_db() -> None:
    repo = auth._get_user_repository()
    active_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    expired_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)

    repo.revoke_token("active-jti", active_expiry)
    repo.revoke_token("expired-jti", expired_expiry)

    with repo._connection() as conn:
        rows = conn.execute("SELECT jti FROM revoked_tokens ORDER BY jti").fetchall()
    assert [row[0] for row in rows] == ["active-jti"]
    assert repo.is_token_revoked("active-jti") is True
    assert repo.is_token_revoked("expired-jti") is False


def test_revoked_bearer_token_is_rejected() -> None:
    _ensure_user("revoked-user")
    token = auth.create_access_token({"sub": "revoked-user"}, timedelta(minutes=30))
    payload = jwt.decode(
        token,
        auth.SECRET_KEY,
        algorithms=[auth.ALGORITHM],
        audience=auth.TOKEN_AUDIENCE,
        issuer=auth.TOKEN_ISSUER,
    )
    auth.revoke_token(
        payload["jti"],
        datetime.fromtimestamp(int(payload["exp"]), timezone.utc),
    )

    client = TestClient(app)
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked"


def test_oidc_authorize_redirects_with_pkce_state(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, str | None] = {}

    monkeypatch.setattr(auth_router_module.oidc_client, "OIDC_ENABLED", True)
    monkeypatch.setattr(
        auth_router_module.oidc_client,
        "build_authorization_url",
        lambda redirect_uri=None: (
            "https://idp.example/authorize?code_challenge=abc123&code_challenge_method=S256",
            "state-1",
            "nonce-1",
            "verifier-1",
        ),
    )
    monkeypatch.setattr(
        auth_router_module.oidc_client,
        "store_oidc_state",
        lambda state, nonce, code_verifier, redirect_uri=None, ttl_seconds=600: stored.update(
            {
                "state": state,
                "nonce": nonce,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            }
        ),
    )

    client = TestClient(app)
    response = client.get(
        "/oidc/authorize",
        params={"redirect_uri": "https://app.example/oidc/callback"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://idp.example/authorize?")
    assert stored == {
        "state": "state-1",
        "nonce": "nonce-1",
        "code_verifier": "verifier-1",
        "redirect_uri": "https://app.example/oidc/callback",
    }


def test_oidc_callback_completes_pkce_login_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    session_calls: list[dict[str, object]] = []

    monkeypatch.setattr(auth_router_module.oidc_client, "OIDC_ENABLED", True)
    monkeypatch.setattr(
        auth_router_module.oidc_client,
        "consume_oidc_state",
        lambda state: {
            "nonce": "nonce-1",
            "code_verifier": "verifier-1",
            "redirect_uri": "https://app.example/oidc/callback",
        },
    )
    monkeypatch.setattr(
        auth_router_module.oidc_client,
        "exchange_code_for_tokens",
        lambda code, code_verifier, redirect_uri=None: {"id_token": "mock-id-token"},
    )
    monkeypatch.setattr(
        auth_router_module.oidc_client,
        "validate_id_token",
        lambda id_token, nonce: {"preferred_username": "oidc-user"},
    )
    monkeypatch.setattr(
        auth_router_module.oidc_client,
        "create_user_session",
        lambda **kwargs: session_calls.append(kwargs) or "session-1",
    )

    client = TestClient(app)
    response = client.get("/oidc/callback?code=auth-code&state=state-1", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/projects"
    assert response.cookies.get("access_token")
    assert auth._get_user_repository().get_user("oidc-user") is not None
    assert session_calls and session_calls[0]["auth_method"] == "oidc"


def test_ldap_login_maps_directory_groups_to_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "LDAP_ROLE_MAP",
        json.dumps({"DocReview-Admins": "admin", "DocReview-Auditors": "auditor"}),
    )
    monkeypatch.setattr(ldap_auth, "authenticate_ldap", lambda username, password: username)
    monkeypatch.setattr(
        ldap_auth,
        "get_ldap_groups",
        lambda username: ["DocReview-Admins", "Ignored", "DocReview-Auditors"],
    )

    assert ldap_auth.ldap_login("alice", "secret") == ("alice", ["admin", "auditor"])


def test_saml_sp_login_and_acs_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saml_router_module.saml_auth, "saml_enabled", lambda: True)
    monkeypatch.setattr(
        saml_router_module.saml_auth,
        "build_auth_request",
        lambda: ("https://idp.example/sso", "request-1"),
    )
    monkeypatch.setattr(
        saml_router_module.saml_auth,
        "process_saml_response",
        lambda response: {"attributes": {"roles": ["auditor"]}, "name_id": "saml-user"},
    )
    monkeypatch.setattr(saml_router_module.saml_auth, "extract_username", lambda attributes: "saml-user")
    monkeypatch.setattr(saml_router_module.saml_auth, "extract_roles", lambda attributes: ["auditor"])

    client = TestClient(app)
    login_response = client.get("/saml/login", follow_redirects=False)
    assert login_response.status_code == 302
    assert login_response.headers["location"] == "https://idp.example/sso"

    acs_response = client.post("/saml/acs", data={"SAMLResponse": "mock-response"}, follow_redirects=False)
    assert acs_response.status_code == 303
    assert acs_response.headers["location"] == "/projects"
    assert acs_response.cookies.get("access_token")
    assert auth._get_user_repository().get_user("saml-user") is not None
    assert rbac.has_role("saml-user", "auditor")


def test_expired_sessions_are_not_listed_or_left_active() -> None:
    now = datetime.now(timezone.utc)
    oidc_client.create_user_session("alice", "expired-jti", now - timedelta(minutes=1))
    oidc_client.create_user_session("alice", "active-jti", now + timedelta(hours=1))

    sessions = oidc_client.list_user_sessions("alice")

    assert [session["jti"] for session in sessions] == ["active-jti"]
    with db_store.get_db().session() as conn:
        row = conn.execute(
            text("SELECT is_active FROM user_sessions WHERE jti = :jti"),
            {"jti": "expired-jti"},
        ).fetchone()
    assert row is not None and row[0] == 0


def test_concurrent_session_limit_revokes_oldest_session(monkeypatch: pytest.MonkeyPatch) -> None:
    revoked: list[str] = []
    now = datetime.now(timezone.utc)
    current_auth_module = importlib.import_module("docreview360.auth")

    monkeypatch.setattr(oidc_client, "SESSION_MAX_CONCURRENT", 1)
    monkeypatch.setattr(current_auth_module, "revoke_token", lambda jti, expires_at: revoked.append(jti))

    oidc_client.create_user_session("alice", "first-jti", now + timedelta(hours=1))
    oidc_client.create_user_session("alice", "second-jti", now + timedelta(hours=1))

    sessions = oidc_client.list_user_sessions("alice")
    assert [session["jti"] for session in sessions] == ["second-jti"]
    assert revoked == ["first-jti"]


def test_idle_timeout_expires_session(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(oidc_client, "IDLE_TIMEOUT_MINUTES", 1)

    oidc_client.create_user_session("alice", "idle-jti", now + timedelta(hours=1))
    with db_store.get_db().session() as conn:
        conn.execute(
            text("UPDATE user_sessions SET last_active_at = :last_active WHERE jti = :jti"),
            {
                "last_active": (now - timedelta(minutes=10)).isoformat(),
                "jti": "idle-jti",
            },
        )

    assert oidc_client.touch_session("idle-jti") is False
    assert oidc_client.list_user_sessions("alice") == []


def test_sessions_endpoints_list_and_revoke_sessions() -> None:
    session_id = oidc_client.create_user_session(
        "alice",
        "sessions-jti",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    client = TestClient(app)

    list_response = client.get("/sessions", headers=_bearer_headers("alice"))
    assert list_response.status_code == 200
    assert any(item["session_id"] == session_id for item in list_response.json())

    revoke_response = client.delete(f"/sessions/{session_id}", headers=_bearer_headers("alice"))
    assert revoke_response.status_code == 200
    assert revoke_response.json()["detail"] == "Session revoked"
    assert oidc_client.list_user_sessions("alice") == []


def test_piv_verify_auth_flow_provisions_user_and_assigns_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from docreview360 import piv_cac

    monkeypatch.setattr(piv_cac, "piv_enabled", lambda: True)
    monkeypatch.setattr(piv_cac, "extract_cert_from_headers", lambda headers: "mock-cert")
    monkeypatch.setattr(
        piv_cac,
        "authenticate_piv",
        lambda cert_pem: ("piv-user", ["auditor"]),
    )

    client = TestClient(app)
    response = client.post("/piv/verify", headers={"X-Client-Cert": "mock-cert"})

    assert response.status_code == 200
    assert response.cookies.get("access_token")
    assert auth._get_user_repository().get_user("piv-user") is not None
    assert rbac.has_role("piv-user", "auditor")


def test_webauthn_registration_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    from docreview360 import webauthn_auth

    monkeypatch.setattr(webauthn_auth, "webauthn_enabled", lambda: True)
    monkeypatch.setattr(
        webauthn_auth,
        "begin_registration",
        lambda username, display_name: (json.dumps({"challenge": "register-challenge"}), "register-challenge"),
    )
    monkeypatch.setattr(
        webauthn_auth,
        "complete_registration",
        lambda username, credential_response_json, challenge_b64url: "credential-1",
    )

    client = TestClient(app)
    begin_response = client.post("/webauthn/register/begin", headers=_bearer_headers("webauthn-user"))
    assert begin_response.status_code == 200
    assert begin_response.json()["challenge"] == "register-challenge"

    complete_response = client.post(
        "/webauthn/register/complete",
        headers=_bearer_headers("webauthn-user"),
        json={"credential": {"id": "credential-1"}, "challenge": "register-challenge"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["credential_id"] == "credential-1"


def test_webauthn_authentication_flow_issues_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from docreview360 import webauthn_auth

    _ensure_user("webauthn-user")
    monkeypatch.setattr(webauthn_auth, "webauthn_enabled", lambda: True)
    monkeypatch.setattr(
        webauthn_auth,
        "begin_authentication",
        lambda username: (json.dumps({"challenge": "auth-challenge"}), "auth-challenge"),
    )
    monkeypatch.setattr(
        webauthn_auth,
        "complete_authentication",
        lambda username, assertion_response_json, challenge_b64url: True,
    )

    client = TestClient(app)
    begin_response = client.post("/webauthn/authenticate/begin", json={"username": "webauthn-user"})
    assert begin_response.status_code == 200
    assert begin_response.json()["challenge"] == "auth-challenge"

    complete_response = client.post(
        "/webauthn/authenticate/complete",
        json={
            "username": "webauthn-user",
            "assertion": {"id": "credential-1"},
            "challenge": "auth-challenge",
        },
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["token_type"] == "bearer"
    assert complete_response.cookies.get("access_token")
    assert any(
        session["auth_method"] == "webauthn"
        for session in oidc_client.list_user_sessions("webauthn-user")
    )


def test_password_expiry_path_blocks_authenticated_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = replace(auth.PasswordPolicy.load(), max_age_days=30)
    _ensure_user("expired-user")
    changed_at = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    with auth._get_user_repository()._connection() as conn:
        conn.execute(
            "UPDATE users SET password_changed_at = ? WHERE username = ?",
            (changed_at, "expired-user"),
        )
        conn.commit()
    monkeypatch.setattr(auth, "_password_policy", lambda: policy)

    client = TestClient(app)
    response = client.get("/me", headers=_bearer_headers("expired-user"))

    assert response.status_code == 403
    assert response.json()["detail"] == "password_expired"


def test_jit_provisioning_creates_user_and_syncs_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_JIT_ROLE_MAP", json.dumps({"IdP-Reviewer": "reviewer"}))
    monkeypatch.setenv("DOCREVIEW360_JIT_DEFAULT_ROLES", "viewer")

    username, roles = jit_provisioning.provision_user_from_claims(
        {"preferred_username": "jit-user", "roles": ["IdP-Reviewer"]},
        "oidc",
    )

    assert username == "jit-user"
    assert roles == ["reviewer", "viewer"]
    assert auth._get_user_repository().get_user("jit-user") is not None
    assert rbac.has_role("jit-user", "reviewer")
    assert rbac.has_role("jit-user", "viewer")


def test_scim_user_and_group_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_SCIM_BEARER_TOKEN", "scim-secret")
    client = TestClient(app)

    create_response = client.post(
        "/scim/v2/Users",
        headers=_scim_headers(),
        json={"userName": "scim-user", "active": True},
    )
    assert create_response.status_code == 201
    assert create_response.json()["userName"] == "scim-user"

    patch_response = client.patch(
        "/scim/v2/Users/scim-user",
        headers=_scim_headers(),
        json={"Operations": [{"op": "replace", "path": "active", "value": False}]},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["active"] is False

    rbac.add_role("scim-user", "viewer")
    group_response = client.get("/scim/v2/Groups/viewer", headers=_scim_headers())
    assert group_response.status_code == 200
    assert any(member["value"] == "scim-user" for member in group_response.json()["members"])


def test_sod_enforces_no_self_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    from docreview360 import documents as documents_module

    monkeypatch.setattr(
        documents_module,
        "documents",
        {"doc-1": SimpleNamespace(uploader="alice")},
    )

    with pytest.raises(sod.SoDViolationError, match="no_self_approval"):
        sod.check_approval_sod("alice", "doc-1", None)


def test_license_report_no_docreview360_gpl_rows() -> None:
    report = _project_file("docs/licenses-report.md")
    assert re.search(r"\| docreview360\s+\|\s+0\.1\.2\s+\|\s+MIT\s+\|", report)
