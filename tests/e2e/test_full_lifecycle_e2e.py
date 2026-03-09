"""Full document lifecycle E2E test: Create → Edit → Review → Approve → Sign → Archive.

These tests exercise the complete happy-path API lifecycle using the Playwright
``page.request.*`` helpers (no frontend interaction required).  A live backend
must be reachable via ``E2E_BACKEND_URL`` and ``E2E_FRONTEND_URL``, which are
provided automatically when running through ``scripts/run_e2e.py``.

Authentication follows the same pattern as ``test_workflow_e2e.py``:
  1. POST ``/token`` to obtain a JWT.
  2. Store it in ``localStorage`` via ``page.evaluate``.
  3. Pass it as a Bearer header for direct API calls.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login_via_api(page: Page, frontend_url: str, backend_url: str, username: str) -> str:
    """Log in, store token in localStorage, and return the raw token string."""
    token_resp = page.request.post(
        f"{backend_url}/token",
        form={"username": username, "password": "password"},
    )
    assert token_resp.ok, f"Login failed for {username!r}: {token_resp.status}"
    access_token = token_resp.json().get("access_token")
    assert access_token, "No access_token in login response"
    page.goto(f"{frontend_url}/login")
    page.evaluate("(token) => localStorage.setItem('access_token', token)", access_token)
    return access_token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Core smoke test — full lifecycle in a single test function
# ---------------------------------------------------------------------------


@pytest.mark.e2e_smoke
def test_full_document_lifecycle(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Smoke test: Create → Upload/Edit → Comment → Approve → Sign → Archive."""

    # ------------------------------------------------------------------
    # Authenticate as alice (reviewer/user role)
    # ------------------------------------------------------------------
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    # ------------------------------------------------------------------
    # Step 1 – Create a new project
    # ------------------------------------------------------------------
    create_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers={**headers, "Content-Type": "application/json"},
        data={
            "name": "Lifecycle Test Project",
            "description": "Full lifecycle E2E test project",
            "doc_type": e2e_seed_data["doc_types"][0],
        },
    )
    assert create_resp.ok, f"POST /projects failed: {create_resp.status} {create_resp.text()}"
    project = create_resp.json()
    project_id: str = project["id"]
    assert project_id

    # Verify the project is retrievable
    get_resp = page.request.get(f"{e2e_backend_url}/projects/{project_id}", headers=headers)
    assert get_resp.ok
    assert get_resp.json()["id"] == project_id

    # ------------------------------------------------------------------
    # Step 2 – Import / upload a document into the project
    # ------------------------------------------------------------------
    import_resp = page.request.post(
        f"{e2e_backend_url}/documents/import",
        headers=headers,
        multipart={
            "file": {
                "name": "lifecycle-test.md",
                "mimeType": "text/markdown",
                "buffer": b"# Lifecycle Test\n\nInitial draft content.",
            },
            "project": project_id,
            "user": "alice",
        },
    )
    assert import_resp.ok, f"POST /documents/import failed: {import_resp.status} {import_resp.text()}"
    document = import_resp.json()
    doc_id: str = document["id"]
    assert doc_id

    # ------------------------------------------------------------------
    # Step 3 – Edit / update the document content
    # ------------------------------------------------------------------
    get_doc_resp = page.request.get(f"{e2e_backend_url}/documents/{doc_id}", headers=headers)
    assert get_doc_resp.ok
    existing_doc = get_doc_resp.json()

    updated_doc = {**existing_doc, "content": "# Lifecycle Test\n\nUpdated content after review edits."}
    update_resp = page.request.put(
        f"{e2e_backend_url}/documents/{doc_id}",
        headers={**headers, "Content-Type": "application/json"},
        data=updated_doc,
    )
    assert update_resp.ok, f"PUT /documents/{doc_id} failed: {update_resp.status} {update_resp.text()}"
    assert update_resp.json()["content"] == "# Lifecycle Test\n\nUpdated content after review edits."

    # ------------------------------------------------------------------
    # Step 4 – Add a reviewer comment on the document
    # ------------------------------------------------------------------
    comment_resp = page.request.post(
        f"{e2e_backend_url}/documents/{doc_id}/comments",
        headers={**headers, "Content-Type": "application/json"},
        data={
            "user": "alice",
            "text": "Reviewed and ready for approval.",
            "tags": ["review", "lgtm"],
        },
    )
    assert comment_resp.ok, f"POST /documents/{doc_id}/comments failed: {comment_resp.status}"
    comment = comment_resp.json()
    assert comment["text"] == "Reviewed and ready for approval."
    comment_id: str = comment["id"]

    # Verify the comment appears in the list
    list_comments_resp = page.request.get(
        f"{e2e_backend_url}/documents/{doc_id}/comments", headers=headers
    )
    assert list_comments_resp.ok
    comment_texts = [c["text"] for c in list_comments_resp.json()]
    assert "Reviewed and ready for approval." in comment_texts

    # ------------------------------------------------------------------
    # Step 5 – Create a project review entry
    # ------------------------------------------------------------------
    workflow_id = e2e_seed_data["project"]["workflow_id"]
    review_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers={**headers, "Content-Type": "application/json"},
        data={
            "comment": "Full lifecycle review complete.",
            "status": "approved",
        },
    )
    assert review_resp.ok, f"POST /projects/{project_id}/reviews failed: {review_resp.status}"
    review = review_resp.json()
    assert review["status"] == "approved"

    # ------------------------------------------------------------------
    # Step 6 – Create an approval record and advance its state to approved
    # ------------------------------------------------------------------
    # Use the seeded project's workflow for approval creation
    seeded_workflow_id = e2e_seed_data["project"]["workflow_id"]
    approval_resp = page.request.post(
        f"{e2e_backend_url}/approvals",
        headers={**headers, "Content-Type": "application/json"},
        data={
            "workflow": seeded_workflow_id,
            "reviewer": "alice",
            "doc_id": doc_id,
            "description": "Lifecycle test approval",
        },
    )
    assert approval_resp.ok, f"POST /approvals failed: {approval_resp.status} {approval_resp.text()}"
    approval = approval_resp.json()
    approval_id: str = approval["id"]
    assert approval_id
    assert approval["state"] in {"pending", "approved"}

    # Advance the approval to approved state
    update_approval_resp = page.request.put(
        f"{e2e_backend_url}/approvals/{approval_id}",
        headers={**headers, "Content-Type": "application/json"},
        data={"state": "approved"},
    )
    assert update_approval_resp.ok, (
        f"PUT /approvals/{approval_id} failed: {update_approval_resp.status}"
    )
    assert update_approval_resp.json()["state"] == "approved"

    # ------------------------------------------------------------------
    # Step 7 – Request a signature for the document
    # ------------------------------------------------------------------
    sign_resp = page.request.post(
        f"{e2e_backend_url}/sign/{doc_id}",
        headers=headers,
        form={"user": "alice"},
    )
    assert sign_resp.ok, f"POST /sign/{doc_id} failed: {sign_resp.status} {sign_resp.text()}"
    sign_result = sign_resp.json()
    sig_id: str = sign_result["id"]
    assert sig_id

    # Poll the signature status
    status_resp = page.request.get(f"{e2e_backend_url}/sign/{sig_id}", headers=headers)
    assert status_resp.ok, f"GET /sign/{sig_id} failed: {status_resp.status}"
    assert "status" in status_resp.json()

    # ------------------------------------------------------------------
    # Step 8 – Archive the document (document-level archive = final storage)
    # ------------------------------------------------------------------
    archive_resp = page.request.post(
        f"{e2e_backend_url}/archive/{doc_id}",
        headers={**headers, "Content-Type": "application/json"},
        data={},
    )
    assert archive_resp.ok, f"POST /archive/{doc_id} failed: {archive_resp.status} {archive_resp.text()}"
    archive = archive_resp.json()
    assert archive["document_id"] == doc_id

    # Confirm it appears in the archive listing
    list_archive_resp = page.request.get(f"{e2e_backend_url}/archive", headers=headers)
    assert list_archive_resp.ok
    archive_ids = [r["document_id"] for r in list_archive_resp.json()]
    assert doc_id in archive_ids


# ---------------------------------------------------------------------------
# Individual lifecycle stage tests (granular coverage)
# ---------------------------------------------------------------------------


def test_lifecycle_create_project(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify project creation returns a valid project with the expected fields."""
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers={**headers, "Content-Type": "application/json"},
        data={"name": "Create-Only Lifecycle Test", "doc_type": e2e_seed_data["doc_types"][0]},
    )
    assert resp.ok, f"Project creation failed: {resp.status}"
    body = resp.json()
    assert body["name"] == "Create-Only Lifecycle Test"
    assert body["id"]


def test_lifecycle_upload_document(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify document upload creates a document linked to the project."""
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    # Create project first
    proj_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers={**headers, "Content-Type": "application/json"},
        data={"name": "Upload Test Project"},
    )
    assert proj_resp.ok
    project_id = proj_resp.json()["id"]

    # Upload a document
    import_resp = page.request.post(
        f"{e2e_backend_url}/documents/import",
        headers=headers,
        multipart={
            "file": {
                "name": "upload-test.md",
                "mimeType": "text/markdown",
                "buffer": b"# Upload Test\n\nContent.",
            },
            "project": project_id,
            "user": "alice",
        },
    )
    assert import_resp.ok, f"Document upload failed: {import_resp.status}"
    doc = import_resp.json()
    assert doc["project"] == project_id


def test_lifecycle_edit_document(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify document content can be updated via PUT /documents/{doc_id}."""
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    # Use the seeded document from e2e_seed_data
    project_id = e2e_seed_data["project"]["id"]
    # Get a document in the project
    docs_resp = page.request.get(f"{e2e_backend_url}/documents", headers=headers)
    assert docs_resp.ok
    project_docs = [d for d in docs_resp.json() if d.get("project") == project_id]
    assert project_docs, "No documents found for the seeded project"
    doc = project_docs[0]
    doc_id = doc["id"]

    updated = {**doc, "content": "Updated content from edit lifecycle test."}
    update_resp = page.request.put(
        f"{e2e_backend_url}/documents/{doc_id}",
        headers={**headers, "Content-Type": "application/json"},
        data=updated,
    )
    assert update_resp.ok, f"Edit failed: {update_resp.status}"
    assert update_resp.json()["content"] == "Updated content from edit lifecycle test."


def test_lifecycle_comment(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify a reviewer comment can be created and listed on a document."""
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    project_id = e2e_seed_data["project"]["id"]
    docs_resp = page.request.get(f"{e2e_backend_url}/documents", headers=headers)
    assert docs_resp.ok
    project_docs = [d for d in docs_resp.json() if d.get("project") == project_id]
    assert project_docs
    doc_id = project_docs[0]["id"]

    comment_resp = page.request.post(
        f"{e2e_backend_url}/documents/{doc_id}/comments",
        headers={**headers, "Content-Type": "application/json"},
        data={"user": "alice", "text": "Needs minor revision in section 2.", "tags": ["review"]},
    )
    assert comment_resp.ok, f"Comment creation failed: {comment_resp.status}"
    assert comment_resp.json()["text"] == "Needs minor revision in section 2."


def test_lifecycle_approve(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify approval creation and state transition to approved."""
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    workflow_id = e2e_seed_data["project"]["workflow_id"]
    project_id = e2e_seed_data["project"]["id"]

    approval_resp = page.request.post(
        f"{e2e_backend_url}/approvals",
        headers={**headers, "Content-Type": "application/json"},
        data={
            "workflow": workflow_id,
            "reviewer": "alice",
            "doc_id": project_id,
            "description": "Approval lifecycle stage test",
        },
    )
    assert approval_resp.ok, f"Create approval failed: {approval_resp.status}"
    approval_id = approval_resp.json()["id"]

    update_resp = page.request.put(
        f"{e2e_backend_url}/approvals/{approval_id}",
        headers={**headers, "Content-Type": "application/json"},
        data={"state": "approved"},
    )
    assert update_resp.ok, f"Update approval failed: {update_resp.status}"
    assert update_resp.json()["state"] == "approved"


def test_lifecycle_sign(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify signature request and status retrieval for a document."""
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    project_id = e2e_seed_data["project"]["id"]
    docs_resp = page.request.get(f"{e2e_backend_url}/documents", headers=headers)
    assert docs_resp.ok
    project_docs = [d for d in docs_resp.json() if d.get("project") == project_id]
    assert project_docs
    doc_id = project_docs[0]["id"]

    sign_resp = page.request.post(
        f"{e2e_backend_url}/sign/{doc_id}",
        headers=headers,
        form={"user": "alice"},
    )
    assert sign_resp.ok, f"Sign request failed: {sign_resp.status}"
    sig_id = sign_resp.json()["id"]
    assert sig_id

    status_resp = page.request.get(f"{e2e_backend_url}/sign/{sig_id}", headers=headers)
    assert status_resp.ok
    assert "status" in status_resp.json()


def test_lifecycle_archive(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify a document can be archived after workflow completion."""
    token = _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(token)

    project_id = e2e_seed_data["project"]["id"]
    docs_resp = page.request.get(f"{e2e_backend_url}/documents", headers=headers)
    assert docs_resp.ok
    project_docs = [d for d in docs_resp.json() if d.get("project") == project_id]
    assert project_docs
    doc_id = project_docs[0]["id"]

    archive_resp = page.request.post(
        f"{e2e_backend_url}/archive/{doc_id}",
        headers={**headers, "Content-Type": "application/json"},
        data={},
    )
    assert archive_resp.ok, f"Archive failed: {archive_resp.status} {archive_resp.text()}"
    record = archive_resp.json()
    assert record["document_id"] == doc_id

    # Verify archive is listed
    list_resp = page.request.get(f"{e2e_backend_url}/archive", headers=headers)
    assert list_resp.ok
    archived_doc_ids = [r["document_id"] for r in list_resp.json()]
    assert doc_id in archived_doc_ids
