# SPDX-License-Identifier: MIT
"""Regression tests for the comments router (anchored comments)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from docreview360 import auth, comments
from docreview360.api import app
from fastapi.testclient import TestClient


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user("alice", "password")
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _clean_comments() -> None:  # type: ignore[return]
    comments.reset_comment_state()
    yield  # type: ignore[misc]
    comments.reset_comment_state()


def _create_project(client: TestClient, project_id: str) -> None:
    resp = client.post(
        "/projects",
        json={"id": project_id, "name": f"Project {project_id}"},
        headers=_alice_headers(),
    )
    assert resp.status_code in (200, 201)


def test_post_comment_with_valid_project_id_succeeds_without_document_id() -> None:
    """POST /comments/{project_id} succeeds even when no document_id is provided."""
    client = TestClient(app)
    _create_project(client, "proj-comments-test")

    resp = client.post(
        "/comments/proj-comments-test",
        json={"text": "This is an anchored comment", "source": "inline"},
        headers=_alice_headers(),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["text"] == "This is an anchored comment"
    assert data["source"] == "inline"
    assert data["project_id"] == "proj-comments-test"


def test_get_comments_returns_inline_and_feedback_source_comments() -> None:
    """GET /comments/{project_id} returns comments with source labels for both inline and feedback."""
    client = TestClient(app)
    _create_project(client, "proj-comments-mixed")

    # Post an inline comment
    r1 = client.post(
        "/comments/proj-comments-mixed",
        json={"text": "Inline anchored comment", "source": "inline"},
        headers=_alice_headers(),
    )
    assert r1.status_code == 201

    # Post a feedback comment
    r2 = client.post(
        "/comments/proj-comments-mixed",
        json={"text": "Feedback comment", "source": "feedback"},
        headers=_alice_headers(),
    )
    assert r2.status_code == 201

    # GET returns both with source labels
    get_resp = client.get("/comments/proj-comments-mixed", headers=_alice_headers())
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["total"] == 2

    sources = {item["source"] for item in body["items"]}
    assert "inline" in sources
    assert "feedback" in sources

    # Check source_label badge values
    labels = {item["source_label"] for item in body["items"]}
    assert "Anchored" in labels  # "inline" source maps to "Anchored" label
    assert "Feedback" in labels
