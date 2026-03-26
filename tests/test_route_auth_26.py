"""Item 26 — Route auth guard coverage tests.

Verifies:
  - All admin-only routes return 403 when called by a non-admin authenticated user
  - All authenticated-only routes return 401 when called without any token
  - Known public routes remain accessible without authentication
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from docreview360 import auth
from docreview360 import rbac as _rbac
from docreview360.api import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _make_token(username: str) -> str:
    return auth.create_access_token({"sub": username}, timedelta(minutes=30))


def _ensure_user(username: str, password: str = "Test@Passw0rd!") -> None:
    try:
        # Use _seed_user to bypass the password policy (demo users have weak passwords).
        auth._get_user_repository()._seed_user(username, password)
    except Exception:
        pass


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    """Headers for alice who has admin + manager roles."""
    _ensure_user("alice")
    try:
        _rbac.set_user_roles("alice", ["admin", "manager", "user"], actor="test", context={})
    except Exception:
        pass
    return {"Authorization": f"Bearer {_make_token('alice')}"}


@pytest.fixture()
def user_headers() -> dict[str, str]:
    """Headers for charlie who has only the 'user' role (not admin)."""
    _ensure_user("charlie")
    try:
        _rbac.set_user_roles("charlie", ["user"], actor="test", context={})
    except Exception:
        pass
    return {"Authorization": f"Bearer {_make_token('charlie')}"}


# ---------------------------------------------------------------------------
# Public routes — accessible without any token
# ---------------------------------------------------------------------------

PUBLIC_ROUTES: list[tuple[str, str]] = [
    # (method, path)
    ("GET", "/health"),
    ("GET", "/ping"),
    ("GET", "/status/public"),
    ("GET", "/"),
    ("GET", "/help"),
]


@pytest.mark.parametrize("method,path", PUBLIC_ROUTES)
def test_public_route_accessible_without_auth(
    client: TestClient, method: str, path: str
) -> None:
    """Public routes must not require a token."""
    resp = client.request(method, path, follow_redirects=False)
    # Accept any 2xx or 3xx (redirect); reject 401 or 403
    assert resp.status_code not in (401, 403), (
        f"{method} {path} should be public but returned {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Authenticated-only routes — return 401 without a token
# ---------------------------------------------------------------------------

AUTHED_ONLY_ROUTES: list[tuple[str, str]] = [
    # Projects
    ("GET", "/projects"),
    ("POST", "/projects"),
    ("GET", "/projects/some-id"),
    # Documents
    ("GET", "/documents"),
    ("GET", "/documents/some-id"),
    # Workflows
    ("GET", "/workflows"),
    ("GET", "/workflow-templates"),
    ("GET", "/workflow_roles"),
    ("POST", "/workflows"),
    ("POST", "/approvals"),
    ("GET", "/approvals"),
    # Signing — now requires auth
    ("GET", "/sign/some-sig"),
    # Templates
    ("GET", "/templates"),
    # Search
    ("GET", "/search?q=test"),
    # Logs (require audit permission, but first need JWT)
    ("GET", "/logs"),
    # Dashboard
    ("GET", "/reports/summary"),
    ("GET", "/metrics/summary"),
    ("GET", "/reports/throughput"),
    ("GET", "/reports/workload"),
    ("GET", "/reports/dashboard"),
    ("GET", "/dashboard/doc-types"),
    ("GET", "/dashboard/widgets"),
    ("GET", "/status/internal"),
    # AI
    ("POST", "/ai/rewrite"),
    ("POST", "/ai/summarize"),
    ("POST", "/chat"),
    # Document types (read)
    ("GET", "/document-types"),
    ("GET", "/document-types/SOP"),
    # Phases (some reads)
    ("GET", "/phases/Draft/usage"),
    # API keys
    ("GET", "/api-keys"),
    # Me
    ("GET", "/me"),
    ("GET", "/profile"),
]


@pytest.mark.parametrize("method,path", AUTHED_ONLY_ROUTES)
def test_authenticated_route_returns_401_without_token(
    client: TestClient, method: str, path: str
) -> None:
    """Authenticated-only routes must return 401 when no Bearer token is provided."""
    # Minimal valid body for POST routes so we get auth errors rather than
    # validation errors
    body: dict | None = None
    if method == "POST":
        body = {}
    resp = client.request(method, path, json=body)
    assert resp.status_code == 401, (
        f"{method} {path} should return 401 without auth, got {resp.status_code}: "
        f"{resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Admin-only routes — return 403 for non-admin authenticated user
# ---------------------------------------------------------------------------

ADMIN_ONLY_ROUTES: list[tuple[str, str]] = [
    # Users CRUD
    ("GET", "/users"),
    ("POST", "/users"),
    ("PUT", "/users/charlie"),
    ("DELETE", "/users/charlie"),
    # RBAC
    ("PUT", "/rbac/role-permissions/user"),
    ("DELETE", "/rbac/role-permissions/user"),
    ("GET", "/rbac/matrix"),
    # Config
    ("GET", "/config"),
    ("PUT", "/config"),
    # Signature provider
    ("GET", "/signature-provider"),
    ("PUT", "/signature-provider"),
    # Environments (now admin-only)
    ("GET", "/environments"),
    ("POST", "/environments/dev"),
    # Admin panel
    ("GET", "/admin/panel"),
    # Document type write ops
    ("POST", "/document-types"),
    ("PUT", "/document-types/SOP"),
    ("DELETE", "/document-types/SOP"),
    ("GET", "/document-types/export"),
    ("POST", "/document-types/import"),
    # Phase write ops
    ("POST", "/phases"),
    ("PUT", "/phases/Draft"),
    ("DELETE", "/phases/Draft"),
    ("PUT", "/phases/Draft/workflow-template"),
    # Template admin ops
    ("POST", "/templates"),
    ("PUT", "/templates/my-template"),
    ("DELETE", "/templates/my-template"),
    # Email templates (admin)
    ("GET", "/email-templates"),
    ("GET", "/email-templates/default"),
    ("POST", "/email-templates"),
    ("PUT", "/email-templates/default"),
    ("DELETE", "/email-templates/default"),
    # Plugin management
    ("POST", "/plugins"),
    ("PUT", "/plugins/myplugin/enable"),
    ("PUT", "/plugins/myplugin/disable"),
    ("DELETE", "/plugins/myplugin"),
    # Plugin marketplace install
    ("POST", "/plugin-marketplace/install"),
    # User import
    ("POST", "/users/import"),
]


@pytest.mark.parametrize("method,path", ADMIN_ONLY_ROUTES)
def test_admin_route_returns_403_for_non_admin(
    client: TestClient, user_headers: dict, method: str, path: str
) -> None:
    """Admin-only routes must return 403 when called by a non-admin user."""
    body: dict | None = None
    if method in ("POST", "PUT"):
        body = {}
    resp = client.request(method, path, json=body, headers=user_headers)
    assert resp.status_code == 403, (
        f"{method} {path} should return 403 for non-admin, got {resp.status_code}: "
        f"{resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Admin-only routes — accessible to admin user
# ---------------------------------------------------------------------------

ADMIN_ACCESSIBLE_ROUTES: list[tuple[str, str]] = [
    ("GET", "/users"),
    ("GET", "/rbac/matrix"),
    ("GET", "/admin/panel"),
    ("GET", "/environments"),
]


@pytest.mark.parametrize("method,path", ADMIN_ACCESSIBLE_ROUTES)
def test_admin_route_accessible_to_admin(
    client: TestClient, admin_headers: dict, method: str, path: str
) -> None:
    """Admin routes must return 2xx (or valid non-403/401) for admin users."""
    resp = client.request(method, path, headers=admin_headers)
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for admin user: {resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Spot-checks: routes changed in this PR
# ---------------------------------------------------------------------------


def test_sign_doc_requires_auth(client: TestClient) -> None:
    """/sign/{doc_id} POST requires authentication."""
    resp = client.post("/sign/test-doc", data={"user": "alice"})
    assert resp.status_code == 401


def test_sign_complete_requires_auth(client: TestClient) -> None:
    """/sign/{sig_id}/complete POST requires authentication."""
    resp = client.post("/sign/test-sig/complete")
    assert resp.status_code == 401


def test_sign_status_requires_auth(client: TestClient) -> None:
    """/sign/{sig_id} GET requires authentication."""
    resp = client.get("/sign/test-sig")
    assert resp.status_code == 401


def test_ai_rewrite_requires_auth(client: TestClient) -> None:
    """/ai/rewrite requires authentication."""
    resp = client.post("/ai/rewrite", json={"text": "hello"})
    assert resp.status_code == 401


def test_ai_summarize_requires_auth(client: TestClient) -> None:
    """/ai/summarize requires authentication."""
    resp = client.post("/ai/summarize", json={"text": "hello"})
    assert resp.status_code == 401


def test_chat_requires_auth(client: TestClient) -> None:
    """/chat requires authentication."""
    resp = client.post("/chat", json={"text": "hello"})
    assert resp.status_code == 401


def test_tools_convert_requires_auth(client: TestClient) -> None:
    """/tools/convert requires authentication."""
    import io
    resp = client.post(
        "/tools/convert",
        data={"output_format": "pdf"},
        files={"file": ("test.docx", io.BytesIO(b"fake"), "application/octet-stream")},
    )
    assert resp.status_code == 401


def test_environments_get_requires_admin(client: TestClient, user_headers: dict) -> None:
    """/environments GET requires admin role."""
    resp = client.get("/environments", headers=user_headers)
    assert resp.status_code == 403


def test_environments_post_requires_admin(client: TestClient, user_headers: dict) -> None:
    """/environments/{name} POST requires admin role."""
    resp = client.post("/environments/prod", headers=user_headers)
    assert resp.status_code == 403


def test_document_types_write_requires_admin(client: TestClient, user_headers: dict) -> None:
    """Document type write operations require admin role."""
    # PUT document-types/{name}
    resp = client.put("/document-types/SOP", json={"name": "SOP", "workflow": []}, headers=user_headers)
    assert resp.status_code == 403
    # DELETE document-types/{name}
    resp = client.delete("/document-types/SOP", headers=user_headers)
    assert resp.status_code == 403


def test_phase_write_requires_admin(client: TestClient, user_headers: dict) -> None:
    """Phase creation and rename require admin role."""
    resp = client.post("/phases", json={"name": "NewPhase"}, headers=user_headers)
    assert resp.status_code == 403
    resp = client.put("/phases/Draft", json={"name": "Renamed"}, headers=user_headers)
    assert resp.status_code == 403


def test_workflow_advance_requires_auth(client: TestClient) -> None:
    """/workflows/{wf_id}/advance requires authentication."""
    resp = client.post("/workflows/wf-123/advance")
    assert resp.status_code == 401


def test_workflow_assign_requires_auth(client: TestClient) -> None:
    """/workflows/{wf_id}/assign requires authentication."""
    resp = client.post("/workflows/wf-123/assign", json={"user": "alice"})
    assert resp.status_code == 401


def test_approval_sign_requires_auth(client: TestClient) -> None:
    """/approvals/{id}/sign requires authentication."""
    resp = client.post("/approvals/appr-123/sign")
    assert resp.status_code == 401


def test_approval_sign_initials_requires_auth(client: TestClient) -> None:
    """/approvals/{id}/sign-initials requires authentication."""
    resp = client.post("/approvals/appr-123/sign-initials", json={"initials": "AB"})
    assert resp.status_code == 401


def test_reports_summary_requires_auth(client: TestClient) -> None:
    """/reports/summary requires authentication."""
    resp = client.get("/reports/summary")
    assert resp.status_code == 401


def test_dashboard_widgets_requires_auth(client: TestClient) -> None:
    """/dashboard/widgets requires authentication."""
    resp = client.get("/dashboard/widgets")
    assert resp.status_code == 401


def test_status_internal_requires_auth(client: TestClient) -> None:
    """/status/internal requires authentication."""
    resp = client.get("/status/internal")
    assert resp.status_code == 401


def test_document_types_get_requires_auth(client: TestClient) -> None:
    """/document-types requires authentication."""
    resp = client.get("/document-types")
    assert resp.status_code == 401


def test_share_token_public(client: TestClient) -> None:
    """/share/{token} is public (no auth needed — returns 404 for unknown token)."""
    resp = client.get("/share/nonexistent-token")
    # Public route: should get 404 (not found), not 401 or 403
    assert resp.status_code not in (401, 403)
