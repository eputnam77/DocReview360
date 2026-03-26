# SPDX-License-Identifier: MIT
"""Tests for document branch/merge (parallel review tracks) — RELEASE_CHECKLIST.md line 244."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


@pytest.fixture()
def client_with_doc():
    """Return a TestClient and create a minimal project + document for branch tests."""
    from docreview360 import auth, rbac
    from docreview360.api import app
    from docreview360.db_store import get_db
    from docreview360.models import Document, Project
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=True)

    # Create admin user + token (using demo user "alice" with known password)
    try:
        auth.create_user("alice", "password")
    except Exception:
        pass
    rbac.add_role("alice", "admin")
    token_resp = client.post("/token", data={"username": "alice", "password": "password"})
    assert token_resp.status_code == 200, token_resp.text
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project + document in DB
    with get_db().orm_session() as db:
        from docreview360.doc_types import list_document_types
        doc_types = list_document_types()
        dt_id = doc_types[0].id if doc_types else 1
        proj = Project(name="BranchTestProject", document_type_id=dt_id)
        db.add(proj)
        db.flush()
        doc = Document(id="test-branch-doc-001", project_id=proj.id, content="Initial content")
        db.add(doc)
        db.flush()
        project_id = proj.id

    return client, headers, "test-branch-doc-001"


def test_create_branch(client_with_doc):
    client, headers, doc_id = client_with_doc
    resp = client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "review-track-1", "content_snapshot": "Branch content v1"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["branch_name"] == "review-track-1"
    assert data["status"] == "open"
    assert data["document_id"] == doc_id
    assert data["content_snapshot"] == "Branch content v1"


def test_list_branches(client_with_doc):
    client, headers, doc_id = client_with_doc
    # Create two branches
    client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "branch-a", "content_snapshot": "Content A"},
        headers=headers,
    )
    client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "branch-b", "content_snapshot": "Content B"},
        headers=headers,
    )
    resp = client.get(f"/documents/{doc_id}/branches", headers=headers)
    assert resp.status_code == 200, resp.text
    branches = resp.json()
    names = [b["branch_name"] for b in branches]
    assert "branch-a" in names
    assert "branch-b" in names


def test_get_branch(client_with_doc):
    client, headers, doc_id = client_with_doc
    create_resp = client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "get-test", "content_snapshot": "test"},
        headers=headers,
    )
    branch_id = create_resp.json()["id"]
    resp = client.get(f"/documents/{doc_id}/branches/{branch_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == branch_id


def test_update_branch_content(client_with_doc):
    client, headers, doc_id = client_with_doc
    create_resp = client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "update-test", "content_snapshot": "old content"},
        headers=headers,
    )
    branch_id = create_resp.json()["id"]
    resp = client.put(
        f"/documents/{doc_id}/branches/{branch_id}/content",
        json={"content_snapshot": "updated content"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["content_snapshot"] == "updated content"


def test_merge_branch(client_with_doc):
    client, headers, doc_id = client_with_doc
    create_resp = client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "merge-test", "content_snapshot": "Merged content"},
        headers=headers,
    )
    branch_id = create_resp.json()["id"]
    resp = client.post(
        f"/documents/{doc_id}/branches/{branch_id}/merge",
        json={"merge_strategy": "overwrite"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "merged"
    assert data["merged_by"] == "alice"
    assert data["new_revision_id"] is not None


def test_close_branch(client_with_doc):
    client, headers, doc_id = client_with_doc
    create_resp = client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "close-test", "content_snapshot": "abandon me"},
        headers=headers,
    )
    branch_id = create_resp.json()["id"]
    resp = client.post(
        f"/documents/{doc_id}/branches/{branch_id}/close",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "closed"


def test_merge_already_merged_branch(client_with_doc):
    """Merging a merged branch should return 409."""
    client, headers, doc_id = client_with_doc
    create_resp = client.post(
        f"/documents/{doc_id}/branches",
        json={"branch_name": "double-merge", "content_snapshot": "some content"},
        headers=headers,
    )
    branch_id = create_resp.json()["id"]
    # First merge
    client.post(
        f"/documents/{doc_id}/branches/{branch_id}/merge",
        json={"merge_strategy": "overwrite"},
        headers=headers,
    )
    # Second merge should fail
    resp = client.post(
        f"/documents/{doc_id}/branches/{branch_id}/merge",
        json={"merge_strategy": "overwrite"},
        headers=headers,
    )
    assert resp.status_code == 409, resp.text


def test_branch_not_found(client_with_doc):
    client, headers, doc_id = client_with_doc
    resp = client.get(f"/documents/{doc_id}/branches/nonexistent-id", headers=headers)
    assert resp.status_code == 404
