"""Smoke tests ensuring route groups respond with expected status codes.

Each test verifies at minimum:
  - Unauthenticated → 401
  - Authenticated valid request → 2xx or expected 4xx shape
"""

from datetime import timedelta
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for alice (admin + manager)."""
    from docreview360 import rbac as _rbac

    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    # Ensure alice has admin + manager roles so role-restricted smoke tests pass.
    try:
        _rbac.set_user_roles("alice", ["admin", "manager", "user"], actor="test", context={})
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def alice_headers() -> dict[str, str]:
    return _alice_headers()


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


def test_login_bad_credentials(client: TestClient) -> None:
    resp = client.post("/token", data={"username": "nobody", "password": "wrong"})
    assert resp.status_code in (400, 401, 403, 422)


def test_login_success(client: TestClient) -> None:
    resp = client.post("/token", data={"username": "alice", "password": "password"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_users_me_unauthenticated(client: TestClient) -> None:
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_users_me_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/users/me", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


# ---------------------------------------------------------------------------
# Template routes
# ---------------------------------------------------------------------------


def test_templates_list_unauthenticated(client: TestClient) -> None:
    resp = client.get("/templates")
    assert resp.status_code == 401


def test_templates_list_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/templates", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_template_create_and_get(client: TestClient, alice_headers: dict) -> None:
    payload = {
        "name": "_smoke_test_tmpl",
        "content": "<p>smoke</p>",
        "metadata": {"label": "Smoke", "format": "HTML", "type": "tiptap"},
    }
    resp = client.post("/templates", json=payload, headers=alice_headers)
    assert resp.status_code in (200, 201, 409), resp.text  # 409 if already exists

    resp = client.get("/templates/_smoke_test_tmpl", headers=alice_headers)
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "template_name",
    [
        "doc_type::Manual / Handbook",
        "doc_type::API Manual / API Reference",
        "doc_type::Briefing / Slide Deck",
    ],
)
def test_template_routes_support_names_with_slashes(
    client: TestClient,
    alice_headers: dict,
    template_name: str,
) -> None:
    client.get("/templates", headers=alice_headers)
    encoded_name = quote(template_name, safe="")

    resp = client.get(f"/templates/{encoded_name}", headers=alice_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == template_name

    download_resp = client.get(f"/templates/{encoded_name}/download", headers=alice_headers)
    assert download_resp.status_code == 200, download_resp.text
    assert download_resp.headers["content-disposition"].startswith("attachment;")


def test_email_templates_list_unauthenticated(client: TestClient) -> None:
    resp = client.get("/email-templates")
    assert resp.status_code == 401


def test_email_templates_list_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/email-templates", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Workflow template routes
# ---------------------------------------------------------------------------


def test_workflow_templates_list_unauthenticated(client: TestClient) -> None:
    resp = client.get("/workflow-templates")
    assert resp.status_code == 401


def test_workflow_templates_list_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/workflow-templates", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_workflow_template_create(client: TestClient, alice_headers: dict) -> None:
    payload = {
        "name": "_smoke_wf_template",
        "steps": [{"role": "reviewer", "action": "approve", "order": 1}],
    }
    resp = client.post("/workflow-templates", json=payload, headers=alice_headers)
    assert resp.status_code in (200, 201, 409), resp.text


# ---------------------------------------------------------------------------
# RBAC routes
# ---------------------------------------------------------------------------


def test_rbac_matrix_unauthenticated(client: TestClient) -> None:
    resp = client.get("/rbac/matrix")
    assert resp.status_code == 401


def test_rbac_matrix_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/rbac/matrix", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Response is {"matrix": {...}, "roles": [...], "permissions": [...], ...}
    assert "admin" in data.get("matrix", data)


def test_rbac_role_permissions_list(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/rbac/role-permissions", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# User management routes
# ---------------------------------------------------------------------------


def test_users_list_unauthenticated(client: TestClient) -> None:
    resp = client.get("/users")
    assert resp.status_code == 401


def test_users_list_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/users", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Dashboard routes
# ---------------------------------------------------------------------------


def test_dashboard_user_unauthenticated(client: TestClient) -> None:
    # /dashboard/user uses X-User header, not Bearer auth; missing header → 401.
    resp = client.get("/dashboard/user")
    assert resp.status_code == 401


def test_dashboard_user_authenticated(client: TestClient, alice_headers: dict) -> None:
    # /dashboard/user reads X-User header (not Bearer auth).
    resp = client.get("/dashboard/user", headers={**alice_headers, "X-User": "alice"})
    assert resp.status_code == 200


def test_dashboard_manager(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/dashboard/manager", headers=alice_headers)
    assert resp.status_code == 200


def test_dashboard_admin(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/dashboard/admin", headers=alice_headers)
    assert resp.status_code == 200


def test_dashboard_widgets(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/dashboard/widgets", headers=alice_headers)
    assert resp.status_code == 200


def test_dashboard_executive_summary(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/dashboard/executive-summary", headers=alice_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Approvals routes
# ---------------------------------------------------------------------------


def test_approvals_list_unauthenticated(client: TestClient) -> None:
    resp = client.get("/approvals")
    assert resp.status_code == 401


def test_approvals_list_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/approvals", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_approval_not_found(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/approvals/nonexistent-id", headers=alice_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Workflow routes
# ---------------------------------------------------------------------------


def test_workflows_list_unauthenticated(client: TestClient) -> None:
    resp = client.get("/workflows")
    assert resp.status_code == 401


def test_workflows_list_authenticated(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/workflows", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_workflow_roles(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/workflow_roles", headers=alice_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)



# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check_returns_db_status(client: TestClient) -> None:
    """Health endpoint should report DB connectivity and return 200 when healthy."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["db"] == "ok"


def test_health_check_includes_json_content_type(client: TestClient) -> None:
    resp = client.get("/health")
    assert "application/json" in resp.headers.get("content-type", "")
