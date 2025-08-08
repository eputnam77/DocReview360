from docreview360.api import app
from docreview360.workflows import create_workflow
from fastapi.testclient import TestClient


def test_gzip_middleware() -> None:
    assert any(getattr(m.cls, "__name__", "") == "GZipMiddleware" for m in app.user_middleware)


def test_list_projects() -> None:
    client = TestClient(app)
    resp = client.get("/projects")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Example"


def test_list_documents() -> None:
    client = TestClient(app)
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    resp = client.get("/documents")
    assert any(d["id"] == doc_id for d in resp.json())


def test_metrics_and_audit_endpoints() -> None:
    client = TestClient(app)

    # metrics summary mirrors /reports/summary
    resp1 = client.get("/metrics/summary")
    assert resp1.status_code == 200
    resp2 = client.get("/reports/summary")
    assert resp1.json() == resp2.json()

    # audit endpoint mirrors /logs
    client.get("/projects")  # trigger a log via dependency
    resp3 = client.get("/api/audit")
    resp4 = client.get("/logs")
    assert resp3.status_code == 200
    assert resp3.json() == resp4.json()


def test_start_workflow_endpoint() -> None:
    client = TestClient(app)
    wf = create_workflow("p194", ["draft", "review"])
    resp = client.post(f"/workflows/{wf.id}/start", data={"title": "t"})
    assert resp.status_code == 200
    assert resp.json()["id"] == wf.id
    assert resp.json()["document"]


def test_update_project_endpoint() -> None:
    client = TestClient(app)
    client.post("/projects", json={"id": "pedit", "name": "Old"})
    resp = client.put("/projects/pedit", json={"name": "New", "user": "bob"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New"
    assert data["user"] == "bob"


def test_update_project_with_formdata() -> None:
    """Test project update with FormData (frontend compatibility)."""
    client = TestClient(app)

    # Create a test project
    client.post("/projects", json={"id": "pedit-form", "name": "Old Project"})

    # Update with FormData (simulating frontend request)
    resp = client.put(
        "/projects/pedit-form",
        data={
            "name": "Updated Project",
            "user": "alice",
            "doc_type": "Advisory Circular",
            "title": "Updated Title",
            "description": "Updated description"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Project"  # Should use title as name
    assert data["user"] == "alice"
    assert data["doc_type"] == "Advisory Circular"


def test_update_project_with_file_upload() -> None:
    """Test project update with file upload."""
    client = TestClient(app)

    # Create a test project
    client.post("/projects", json={"id": "pedit-file", "name": "File Test Project"})

    # Update with file upload
    resp = client.put(
        "/projects/pedit-file",
        data={
            "name": "File Updated Project",
            "user": "bob",
            "doc_type": "Policy Statement"
        },
        files={"file": ("test_document.md", "This is test content", "text/markdown")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "File Updated Project"
    assert data["user"] == "bob"
    assert data["doc_type"] == "Policy Statement"

    # Verify that a document was created for this project
    docs_resp = client.get("/documents")
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    project_docs = [d for d in docs if d.get("project") == "pedit-file"]
    assert len(project_docs) > 0


def test_update_project_not_found() -> None:
    """Test project update with non-existent project ID."""
    client = TestClient(app)

    resp = client.put(
        "/projects/nonexistent",
        data={"name": "New Name"}
    )
    assert resp.status_code == 404


def test_update_project_partial_fields() -> None:
    """Test project update with only some fields provided."""
    client = TestClient(app)

    # Create a test project
    client.post(
        "/projects",
        json={
            "id": "pedit-partial",
            "name": "Original Name",
            "user": "original",
        },
    )

    # Update only the name
    resp = client.put(
        "/projects/pedit-partial",
        data={"name": "Only Name Updated"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Only Name Updated"
    assert data["user"] == "original"  # Should remain unchanged


def test_environments_endpoint() -> None:
    """Test the environments endpoint that frontend is trying to access."""
    client = TestClient(app)

    resp = client.get("/environments")
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
    resp = client.get("/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "username" in data
    assert "is_admin" in data


def test_project_edit_frontend_compatibility() -> None:
    """Test that project editing works with the exact format the frontend sends."""
    client = TestClient(app)

    # Create a test project
    client.post("/projects", json={"id": "frontend-test", "name": "Frontend Test Project"})

    # Simulate the exact frontend FormData format
    resp = client.put(
        "/projects/frontend-test",
        data={
            "docId": "DOC-123",
            "title": "Updated Document Title",
            "sme": "John Doe",
            "docType": "Advisory Circular",
            "description": "Updated project description"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Document Title"  # title should map to name
    assert data["user"] == "John Doe"  # sme should map to user
    assert data["doc_type"] == "Advisory Circular"
