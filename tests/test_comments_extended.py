"""Tests for extended comment functionality: tags, status, and PUT endpoint."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.comments import (
    CommentModel,
    add_comment,
    list_comments,
    reset_comment_state,
    update_comment,
    COMMENT_STATUSES,
    COMMENT_TAGS,
)
from docreview360.documents import documents, import_document


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_comment_state()


# ---------------------------------------------------------------------------
# Unit tests for comment model extensions
# ---------------------------------------------------------------------------


def test_comment_has_default_status() -> None:
    comment = add_comment("doc1", "alice", "Hello")
    assert comment.status == "open"


def test_comment_has_default_empty_tags() -> None:
    comment = add_comment("doc1", "alice", "Hello")
    assert comment.tags == []


def test_add_comment_with_tags() -> None:
    comment = add_comment("doc1", "alice", "Legal concern", tags=["legal", "policy"])
    assert "legal" in comment.tags
    assert "policy" in comment.tags


def test_add_comment_ignores_invalid_tags() -> None:
    comment = add_comment("doc1", "alice", "Note", tags=["legal", "invalid_tag"])
    assert "legal" in comment.tags
    assert "invalid_tag" not in comment.tags


def test_update_comment_status() -> None:
    comment = add_comment("doc1", "alice", "Review this")
    updated = update_comment("doc1", comment.id, status="resolved")
    assert updated.status == "resolved"
    # Persisted in list
    comments = list_comments("doc1")
    assert comments[0].status == "resolved"


def test_update_comment_tags() -> None:
    comment = add_comment("doc1", "alice", "Style note")
    updated = update_comment("doc1", comment.id, tags=["style", "technical"])
    assert "style" in updated.tags
    assert "technical" in updated.tags


def test_update_comment_text() -> None:
    comment = add_comment("doc1", "alice", "Original text")
    updated = update_comment("doc1", comment.id, text="Updated text")
    assert "Updated text" in updated.raw_text


def test_update_comment_invalid_status_raises() -> None:
    comment = add_comment("doc1", "alice", "Note")
    with pytest.raises(ValueError, match="invalid status"):
        update_comment("doc1", comment.id, status="flying")


def test_update_comment_not_found_raises() -> None:
    add_comment("doc1", "alice", "Note")
    with pytest.raises(KeyError):
        update_comment("doc1", "nonexistent-id", status="resolved")


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Return Authorization headers for 'alice' (admin test user)."""
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def doc_id() -> str:
    """Create a document directly via the module and return its ID."""
    doc = import_document("test.html", b"<p>Test content</p>", user="alice")
    yield doc.id
    documents.pop(doc.id, None)


def test_post_comment_with_tags(
    client: TestClient, doc_id: str, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        f"/documents/{doc_id}/comments",
        json={"user": "alice", "text": "Legal note", "tags": ["legal"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "legal" in data["tags"]
    assert data["status"] == "open"


def test_get_comments_returns_tags_and_status(
    client: TestClient, doc_id: str, auth_headers: dict[str, str]
) -> None:
    client.post(
        f"/documents/{doc_id}/comments",
        json={"user": "alice", "text": "Style note", "tags": ["style"]},
        headers=auth_headers,
    )
    resp = client.get(f"/documents/{doc_id}/comments", headers=auth_headers)
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) == 1
    assert "style" in comments[0]["tags"]
    assert comments[0]["status"] == "open"


def test_put_comment_updates_status(
    client: TestClient, doc_id: str, auth_headers: dict[str, str]
) -> None:
    post_resp = client.post(
        f"/documents/{doc_id}/comments",
        json={"user": "alice", "text": "Open issue"},
        headers=auth_headers,
    )
    comment_id = post_resp.json()["id"]

    put_resp = client.put(
        f"/documents/{doc_id}/comments/{comment_id}",
        json={"status": "resolved"},
        headers=auth_headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["status"] == "resolved"


def test_put_comment_updates_tags(
    client: TestClient, doc_id: str, auth_headers: dict[str, str]
) -> None:
    post_resp = client.post(
        f"/documents/{doc_id}/comments",
        json={"user": "alice", "text": "Note"},
        headers=auth_headers,
    )
    comment_id = post_resp.json()["id"]

    put_resp = client.put(
        f"/documents/{doc_id}/comments/{comment_id}",
        json={"tags": ["technical", "policy"]},
        headers=auth_headers,
    )
    assert put_resp.status_code == 200
    tags = put_resp.json()["tags"]
    assert "technical" in tags
    assert "policy" in tags


def test_put_comment_invalid_status_returns_422(
    client: TestClient, doc_id: str, auth_headers: dict[str, str]
) -> None:
    post_resp = client.post(
        f"/documents/{doc_id}/comments",
        json={"user": "alice", "text": "Note"},
        headers=auth_headers,
    )
    comment_id = post_resp.json()["id"]

    resp = client.put(
        f"/documents/{doc_id}/comments/{comment_id}",
        json={"status": "flying"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_put_comment_not_found_returns_404(
    client: TestClient, doc_id: str, auth_headers: dict[str, str]
) -> None:
    resp = client.put(
        f"/documents/{doc_id}/comments/nonexistent-id",
        json={"status": "resolved"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_put_comment_document_not_found_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.put(
        "/documents/no-such-doc/comments/no-such-comment",
        json={"status": "resolved"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
