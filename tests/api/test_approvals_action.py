# SPDX-License-Identifier: MIT
"""Regression tests for POST /projects/{project_id}/approvals/{approval_id}/approve."""
from __future__ import annotations

from datetime import timedelta

import pytest
from docreview360 import auth
from docreview360.api import app
from docreview360.approvals import reset_approvals
from fastapi.testclient import TestClient


def _token_headers(username: str) -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            username,
            "password",
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _alice_headers() -> dict[str, str]:
    return _token_headers("alice")


def _bob_headers() -> dict[str, str]:
    return _token_headers("bob")


@pytest.fixture(autouse=True)
def _clean_approvals() -> None:  # type: ignore[return]
    reset_approvals()
    yield  # type: ignore[misc]
    reset_approvals()


def _setup(client: TestClient) -> tuple[str, str]:
    """Create a project, workflow, and approval row for alice. Returns (project_id, approval_id)."""
    alice = _alice_headers()

    # Create project
    resp = client.post(
        "/projects",
        json={"id": "proj-approve-action", "name": "Approve Action Test"},
        headers=alice,
    )
    assert resp.status_code in (200, 201)
    project_id = resp.json()["id"]

    # Create workflow
    wf_resp = client.post(
        "/workflows",
        json={"project": project_id, "phases": ["draft", "approval"]},
        headers=alice,
    )
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    # Create approval assigned to alice
    appr_resp = client.post(
        "/approvals",
        json={"workflow": wf_id, "reviewer": "alice", "doc_id": wf_id},
        headers=alice,
    )
    assert appr_resp.status_code == 201
    approval_id = appr_resp.json()["id"]

    return project_id, approval_id


def test_approver_can_approve_own_row() -> None:
    """Assigned approver successfully approves their row."""
    client = TestClient(app)
    project_id, approval_id = _setup(client)

    resp = client.post(
        f"/projects/{project_id}/approvals/{approval_id}/approve",
        json={"method": "initials", "note": "LGTM"},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] == "approved"


def test_non_approver_cannot_approve_others_row() -> None:
    """User who is not the assigned approver receives 403."""
    client = TestClient(app)
    project_id, approval_id = _setup(client)

    resp = client.post(
        f"/projects/{project_id}/approvals/{approval_id}/approve",
        json={"method": "initials", "note": ""},
        headers=_bob_headers(),
    )
    assert resp.status_code == 403


def test_already_approved_row_returns_409() -> None:
    """Attempting to approve an already-approved row returns 409."""
    client = TestClient(app)
    project_id, approval_id = _setup(client)

    # First approval succeeds
    resp = client.post(
        f"/projects/{project_id}/approvals/{approval_id}/approve",
        json={"method": "initials", "note": ""},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200

    # Second attempt returns 409
    resp2 = client.post(
        f"/projects/{project_id}/approvals/{approval_id}/approve",
        json={"method": "initials", "note": ""},
        headers=_alice_headers(),
    )
    assert resp2.status_code == 409
