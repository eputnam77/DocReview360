from pathlib import Path
from uuid import uuid4

from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient


def _auth_headers(username: str, *, admin: bool = False) -> dict[str, str]:
    auth.USER_REPOSITORY.create_user(
        username,
        auth.DEMO_USER_DEFAULTS.get(username, {}).get("password", "StrongPassw0rd!"),
        otp_secret=auth.DEMO_USER_DEFAULTS.get(username, {}).get("otp_secret"),
    )
    if admin:
        rbac.add_role(username, "admin")
    token = auth.create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


def _configure_repositories() -> None:
    base = Path(".tmp") / f"security-authz-{uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    auth.configure_user_repository(base / "users.db")
    rbac.configure_role_repository(base / "roles.db")


def test_projects_and_documents_require_auth() -> None:
    _configure_repositories()
    client = TestClient(app)

    projects_resp = client.get("/projects")
    documents_resp = client.get("/documents")

    assert projects_resp.status_code == 401
    assert documents_resp.status_code == 401


def test_project_document_access_denied_for_unassigned_user() -> None:
    _configure_repositories()
    client = TestClient(app)
    admin_headers = _auth_headers("alice", admin=True)
    bob_headers = _auth_headers("bob")

    create_project = client.post(
        "/projects",
        json={"id": "authz-project", "name": "Authz Project", "user": "alice"},
        headers=admin_headers,
    )
    assert create_project.status_code == 201

    upload = client.post(
        "/documents/import",
        files={"file": ("authz.md", b"# Secret", "text/markdown")},
        data={"project": "authz-project", "user": "alice"},
        headers=admin_headers,
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    bob_project = client.get("/projects/authz-project", headers=bob_headers)
    bob_document = client.get(f"/documents/{doc_id}", headers=bob_headers)
    assert bob_project.status_code == 403
    assert bob_document.status_code == 403

    alice_headers = _auth_headers("alice", admin=True)
    alice_project = client.get("/projects/authz-project", headers=alice_headers)
    alice_document = client.get(f"/documents/{doc_id}", headers=alice_headers)
    assert alice_project.status_code == 200
    assert alice_document.status_code == 200
