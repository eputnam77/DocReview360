import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.approvals import approvals
from docreview360.workflows import workflows


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

    response = client.post("/projects", json=payload)
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
