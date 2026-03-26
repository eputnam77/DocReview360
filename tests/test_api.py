from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.logs import clear_logs, log_event
from docreview360.workflows import create_workflow


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for a test 'alice' admin user."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass  # user may already exist
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_gzip_middleware() -> None:
    assert any(getattr(m.cls, "__name__", "") == "GZipMiddleware" for m in app.user_middleware)


def test_security_headers_middleware() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_cors_restricts_methods() -> None:
    """CORS should not allow TRACE or CONNECT methods."""
    from docreview360.api import app as _app

    cors_middleware = next(
        (m for m in _app.user_middleware if getattr(m.cls, "__name__", "") == "CORSMiddleware"),
        None,
    )
    assert cors_middleware is not None
    allowed = cors_middleware.kwargs.get("allow_methods", [])
    assert "TRACE" not in allowed
    assert "CONNECT" not in allowed
    assert "*" not in allowed


def test_list_projects() -> None:
    client = TestClient(app)
    resp = client.get("/projects", headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.json()["items"][0]["name"] == "Demo Project"


def test_demo_review_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/projects/demo-project/reviews", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["comment"] == "Looks good!" for r in data)


def test_list_documents() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.get("/documents", headers=hdrs)
    assert resp.status_code == 200

    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
        headers=hdrs,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    resp = client.get("/documents", headers=hdrs)
    assert any(d["id"] == doc_id for d in resp.json()["items"])


def test_metrics_and_audit_endpoints() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    # metrics summary mirrors /reports/summary
    resp1 = client.get("/metrics/summary", headers=hdrs)
    assert resp1.status_code == 200
    resp2 = client.get("/reports/summary", headers=hdrs)
    assert resp1.json() == resp2.json()

    # audit endpoint mirrors /logs
    client.get("/projects", headers=hdrs)  # trigger a log via dependency
    audit_headers = {**hdrs, "X-User": "alice"}
    resp3 = client.get("/api/audit", headers=audit_headers)
    resp4 = client.get("/logs", headers=audit_headers)
    assert resp3.status_code == 200
    data3 = [e for e in resp3.json() if e["action"] != "audit_log_access"]
    data4 = [e for e in resp4.json() if e["action"] != "audit_log_access"]
    assert data3 == data4


def test_audit_pagination() -> None:
    client = TestClient(app)
    clear_logs()
    for i in range(3):
        log_event(f"event_{i}", user_id="alice")
    hdrs = {**_alice_headers(), "X-User": "alice"}
    resp = client.get("/api/audit?page=0&size=2", headers=hdrs)
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    resp2 = client.get("/api/audit?page=1&size=2", headers=hdrs)
    assert resp2.status_code == 200
    assert len(resp2.json()) >= 1


def test_start_workflow_endpoint() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    wf = create_workflow("p194", ["draft", "review"])
    resp = client.post(f"/workflows/{wf.id}/start", data={"title": "t"}, headers=hdrs)
    assert resp.status_code == 200
    assert resp.json()["id"] == wf.id
    assert resp.json()["document"]


def test_start_workflow_defaults_title() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    wf = create_workflow("p195", ["draft", "review"])
    resp = client.post(f"/workflows/{wf.id}/start", data={}, headers=hdrs)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == wf.id
    assert payload["document"]


def test_update_project_endpoint() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    client.post("/projects", json={"id": "pedit", "name": "Old"}, headers=hdrs)
    resp = client.put("/projects/pedit", json={"name": "New", "user": "bob"}, headers=hdrs)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New"
    assert data["user"] == "bob"


def test_update_project_with_formdata() -> None:
    """Test project update with FormData (frontend compatibility)."""
    client = TestClient(app)
    hdrs = _alice_headers()

    # Create a test project
    client.post("/projects", json={"id": "pedit-form", "name": "Old Project"}, headers=hdrs)

    # Update with FormData (simulating frontend request)
    resp = client.put(
        "/projects/pedit-form",
        data={
            "name": "Updated Project",
            "user": "alice",
            "doc_type": "Advisory Circular",
            "title": "Updated Title",
            "description": "Updated description",
        },
        headers=hdrs,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Project"  # Should use title as name
    assert data["user"] == "alice"
    assert data["doc_type"] == "Advisory Circular"


def test_update_project_with_file_upload() -> None:
    """Test project update with file upload."""
    client = TestClient(app)
    hdrs = _alice_headers()

    # Create a test project
    client.post("/projects", json={"id": "pedit-file", "name": "File Test Project"}, headers=hdrs)

    # Update with file upload
    resp = client.put(
        "/projects/pedit-file",
        data={"name": "File Updated Project", "user": "bob", "doc_type": "Policy Statement"},
        files={"file": ("test_document.md", "This is test content", "text/markdown")},
        headers=hdrs,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "File Updated Project"
    assert data["user"] == "bob"
    assert data["doc_type"] == "Policy Statement"

    # Verify that a document was created for this project
    docs_resp = client.get("/documents", headers=hdrs)
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    project_docs = [d for d in docs if d.get("project") == "pedit-file"]
    assert len(project_docs) > 0


def test_update_project_not_found() -> None:
    """Test project update with non-existent project ID."""
    client = TestClient(app)

    resp = client.put("/projects/nonexistent", data={"name": "New Name"}, headers=_alice_headers())
    assert resp.status_code == 404


def test_update_project_partial_fields() -> None:
    """Test project update with only some fields provided."""
    client = TestClient(app)
    hdrs = _alice_headers()

    # Create a test project
    client.post(
        "/projects",
        json={
            "id": "pedit-partial",
            "name": "Original Name",
            "user": "original",
        },
        headers=hdrs,
    )

    # Update only the name
    resp = client.put("/projects/pedit-partial", data={"name": "Only Name Updated"}, headers=hdrs)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Only Name Updated"
    assert data["user"] == "original"  # Should remain unchanged


def test_environments_endpoint() -> None:
    """Test the environments endpoint that frontend is trying to access."""
    client = TestClient(app)
    hdrs = _alice_headers()

    resp = client.get("/environments", headers=hdrs)
    assert resp.status_code == 200
    data = resp.json()
    assert "current" in data
    assert "envs" in data


def test_users_me_endpoint() -> None:
    """Test the /api/users/me endpoint that frontend is trying to access."""
    client = TestClient(app)

    # Test without user header
    resp = client.get("/api/users/me")
    assert resp.status_code == 404  # This endpoint doesn't exist, should return 404

    # Test the correct endpoint that does exist
    auth.USER_REPOSITORY.create_user(
        "alice",
        auth.DEMO_USER_DEFAULTS["alice"]["password"],
        otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
    )
    token = auth.create_access_token({"sub": "alice"})
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert "is_admin" in data


def test_project_edit_frontend_compatibility() -> None:
    """Test that project editing works with the exact format the frontend sends."""
    client = TestClient(app)
    hdrs = _alice_headers()

    # Create a test project
    client.post("/projects", json={"id": "frontend-test", "name": "Frontend Test Project"}, headers=hdrs)

    # Simulate the exact frontend FormData format
    resp = client.put(
        "/projects/frontend-test",
        data={
            "docId": "DOC-123",
            "title": "Updated Document Title",
            "sme": "John Doe",
            "docType": "Advisory Circular",
            "description": "Updated project description",
        },
        headers=hdrs,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Document Title"  # title should map to name
    assert data["user"] == "John Doe"  # sme should map to user
    assert data["doc_type"] == "Advisory Circular"


def test_token_revocation_on_logout() -> None:
    """Token should be rejected after logout revokes its JTI."""
    client = TestClient(app)
    hdrs = _alice_headers()

    # Confirm token works before logout.
    resp = client.get("/projects", headers=hdrs)
    assert resp.status_code == 200

    # Extract the raw token to use after logout.
    token = hdrs["Authorization"].split(" ", 1)[1]

    # Logout should revoke the token.
    resp = client.post("/logout", headers=hdrs)
    assert resp.status_code == 200

    # Same token should now be rejected.
    resp = client.get("/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_includes_jti() -> None:
    """Tokens must include a JTI claim for revocation support."""
    from jose import jwt as _jwt

    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=5))
    payload = _jwt.decode(
        token,
        auth.SECRET_KEY,
        algorithms=[auth.ALGORITHM],
        audience=auth.TOKEN_AUDIENCE,
        issuer=auth.TOKEN_ISSUER,
    )
    assert "jti" in payload
    assert len(payload["jti"]) == 32  # 16 bytes hex = 32 chars
    assert "gen" in payload  # token generation claim present


def test_token_generation_invalidates_sessions() -> None:
    """Bumping token_generation invalidates all existing tokens for a user."""
    import uuid

    from fastapi.testclient import TestClient
    from jose import jwt as _jwt

    client = TestClient(app)

    # Create a temporary user to avoid affecting shared state.
    test_user = f"gen_test_{uuid.uuid4().hex[:8]}"
    test_password = "GoodPass123!"
    try:
        auth.USER_REPOSITORY.create_user(test_user, test_password)
    except Exception:
        pass  # policy may reject or user exists

    # Mint a token before generation bump.
    token_before = auth.create_access_token({"sub": test_user}, timedelta(minutes=5))
    hdrs_before = {"Authorization": f"Bearer {token_before}"}

    # The token should work initially.
    resp = client.get("/users/me", headers=hdrs_before)
    # May be 200 or 401 depending on user state, but should not error unexpectedly.
    initial_status = resp.status_code

    # Bump the generation (simulates password change / suspension).
    new_gen = auth.USER_REPOSITORY.bump_token_generation(test_user)
    assert new_gen >= 1

    # Verify the `gen` claim in the old token is now stale.
    payload = _jwt.decode(
        token_before,
        auth.SECRET_KEY,
        algorithms=[auth.ALGORITHM],
        audience=auth.TOKEN_AUDIENCE,
        issuer=auth.TOKEN_ISSUER,
    )
    assert payload["gen"] < new_gen

    # Old token must now be rejected.
    resp = client.get("/users/me", headers=hdrs_before)
    assert resp.status_code == 401

    # A freshly minted token with the new generation must work.
    token_after = auth.create_access_token({"sub": test_user}, timedelta(minutes=5))
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token_after}"})
    assert resp.status_code == 200

    # Cleanup.
    auth.USER_REPOSITORY.delete_user(test_user)
