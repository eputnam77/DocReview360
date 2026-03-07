from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.approvals import approvals
from docreview360.workflows import workflows


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_project_creation_uses_template_workflow() -> None:
    client = TestClient(app)
    workflows.clear()
    approvals.clear()

    payload = {
        "name": "API Workflow",
        "doc_type": "Advisory Circular",
        "phase": "Internal Coordination",
        "workflow": "branch-coordination",
    }

    response = client.post("/projects", json=payload, headers=_alice_headers())
    assert response.status_code == 201

    data = response.json()
    workflow_id = data["workflow"]
    assert workflow_id
    assert workflow_id != payload["phase"]

    workflow = workflows[workflow_id]
    assert workflow.project == data["id"]
    assert workflow.template == payload["workflow"]
    assert workflow.phase == payload["phase"]
    assert workflow.phases[0] == payload["phase"]
    assert workflow.approval_steps

    approval_records = [a for a in approvals.values() if a.workflow == workflow_id]
    assert approval_records
