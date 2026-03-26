from uuid import uuid4

from docreview360 import auth, rbac, settings_manager
from docreview360.api import app
from fastapi.testclient import TestClient

_STRONG_PASSWORD = "Password1!XYZabc"


def _admin_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user("admin_user", _STRONG_PASSWORD)
    except Exception:
        pass
    rbac.add_role("admin_user", "admin")
    token = auth.create_access_token({"sub": "admin_user"})
    return {"Authorization": f"Bearer {token}"}


def _login_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    resp = client.post("/token", data={"username": username, "password": password})
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token
    return {"Authorization": f"Bearer {token}", "X-User": username}


def test_user_lifecycle_from_config_to_workflow(tmp_path) -> None:
    settings_manager.SETTINGS_FILE = tmp_path / "settings.yaml"
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    client = TestClient(app)

    admin_headers = _admin_headers()

    username = f"user_{uuid4().hex[:8]}"
    password = _STRONG_PASSWORD

    resp = client.post(
        "/users",
        headers=admin_headers,
        json={"username": username, "roles": ["user", "reviewer"], "password": password},
    )
    assert resp.status_code == 201

    user_headers = _login_headers(client, username, password)

    profile_resp = client.put(
        "/profile",
        headers=user_headers,
        json={"displayName": "Test User", "email": "test.user@example.com"},
    )
    assert profile_resp.status_code == 200
    assert profile_resp.json()["displayName"] == "Test User"

    dashboard_resp = client.get("/dashboard/user", headers=user_headers)
    assert dashboard_resp.status_code == 200

    doc_types_resp = client.get("/document-types", headers=user_headers)
    assert doc_types_resp.status_code == 200
    doc_types = doc_types_resp.json()
    assert doc_types
    doc_type_name = doc_types[0]["name"]
    phases = doc_types[0].get("phases") or doc_types[0].get("workflow") or []
    assert phases

    templates_resp = client.get("/workflow-templates", headers=user_headers)
    assert templates_resp.status_code == 200
    templates = templates_resp.json()
    assert templates
    workflow_template_id = templates[0]["id"]

    project_resp = client.post(
        "/projects",
        headers=user_headers,
        json={
            "name": f"Project {uuid4().hex[:6]}",
            "document_number": f"DOC-{uuid4().hex[:6]}",
            "doc_type": doc_type_name,
            "phase": phases[0],
            "workflow": workflow_template_id,
        },
    )
    assert project_resp.status_code == 201
    project = project_resp.json()
    project_id = project["id"]
    workflow_id = project.get("workflow")
    assert workflow_id

    update_resp = client.put(
        f"/projects/{project_id}",
        headers=user_headers,
        json={"description": "Updated by user"},
    )
    assert update_resp.status_code == 200

    review_resp = client.post(
        f"/projects/{project_id}/reviews",
        headers=user_headers,
        json={"comment": "Looks good", "status": "approved"},
    )
    assert review_resp.status_code == 201

    import_resp = client.post(
        "/documents/import",
        headers=user_headers,
        files={"file": ("doc.txt", b"Test content", "text/plain")},
        data={"project": project_id, "user": username},
    )
    assert import_resp.status_code == 201
    document_id = import_resp.json()["id"]

    comment_resp = client.post(
        f"/documents/{document_id}/comments",
        headers=user_headers,
        json={"user": username, "text": "Needs minor edits"},
    )
    assert comment_resp.status_code == 201

    approval_resp = client.post(
        "/approvals",
        headers=user_headers,
        json={
            "workflow": workflow_id,
            "reviewer": username,
            "doc_id": document_id,
            "description": "Signature required",
        },
    )
    assert approval_resp.status_code == 201
    approval_id = approval_resp.json()["id"]

    sign_resp = client.post(f"/approvals/{approval_id}/sign", headers=user_headers)
    assert sign_resp.status_code == 200
    sign_payload = sign_resp.json()
    assert sign_payload.get("id")
    assert sign_payload.get("url")
