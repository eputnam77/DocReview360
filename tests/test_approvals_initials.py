"""Tests for the POST /approvals/{approval_id}/sign-initials endpoint."""

import pytest
from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.approvals import approvals, create_approval


@pytest.fixture(autouse=True)
def clear_approvals():
    """Reset in-memory approval store between tests."""
    approvals.clear()
    yield
    approvals.clear()


def _create_workflow(client: TestClient) -> str:
    resp = client.post(
        "/workflows",
        json={"project": "p-initials", "phases": ["review"]},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_approval(client: TestClient, workflow_id: str, reviewer: str = "alice") -> str:
    resp = client.post(
        "/approvals",
        json={"workflow": workflow_id, "reviewer": reviewer, "doc_id": "doc-initials"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestSignInitialsValidation:
    def test_valid_two_letter_initials(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "AB"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "approved"
        assert data["signature"] == "[initials:AB]"

    def test_valid_five_letter_initials(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "ABCDE"})
        assert resp.status_code == 200
        assert resp.json()["state"] == "approved"

    def test_invalid_lowercase_initials(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "ab"})
        assert resp.status_code == 422
        assert "uppercase" in resp.json()["detail"].lower()

    def test_invalid_single_letter(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "A"})
        assert resp.status_code == 422

    def test_invalid_six_letters(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "ABCDEF"})
        assert resp.status_code == 422

    def test_invalid_with_digit(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "A1"})
        assert resp.status_code == 422

    def test_invalid_with_space(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "A B"})
        assert resp.status_code == 422

    def test_empty_initials(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": ""})
        assert resp.status_code == 422


class TestSignInitialsNotFound:
    def test_nonexistent_approval(self) -> None:
        client = TestClient(app)
        resp = client.post("/approvals/does-not-exist/sign-initials", json={"initials": "AB"})
        assert resp.status_code == 404

    def test_missing_body(self) -> None:
        client = TestClient(app)
        resp = client.post("/approvals/any-id/sign-initials", json={})
        assert resp.status_code == 422


class TestSignInitialsIdempotency:
    def test_already_approved_returns_409(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        # First initials sign
        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "EP"})
        assert resp.status_code == 200

        # Second attempt on already-approved approval
        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "EP"})
        assert resp.status_code == 409

    def test_signature_id_format(self) -> None:
        client = TestClient(app)
        wf_id = _create_workflow(client)
        aid = _create_approval(client, wf_id)

        resp = client.post(f"/approvals/{aid}/sign-initials", json={"initials": "JD"})
        assert resp.status_code == 200
        assert resp.json()["signature"] == "[initials:JD]"
