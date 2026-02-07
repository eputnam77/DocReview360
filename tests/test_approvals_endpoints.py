from fastapi.testclient import TestClient

from docreview360.api import app


def _create_workflow(client: TestClient, project_id: str) -> str:
    resp = client.post("/workflows", json={"project": project_id, "phases": ["draft", "approval"]})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_approval(client: TestClient, wf_id: str, reviewer: str = "alice") -> str:
    resp = client.post(
        "/approvals",
        json={
            "workflow": wf_id,
            "reviewer": reviewer,
            "doc_id": wf_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_approval_reminders_and_deletion() -> None:
    client = TestClient(app)
    workflow_id = _create_workflow(client, "proj-remind")
    approval_id = _create_approval(client, workflow_id)

    reminder_resp = client.post(
        "/approvals/remind",
        json={"ids": [approval_id, "missing-id"]},
    )
    assert reminder_resp.status_code == 200
    assert reminder_resp.json() == {"sent": [approval_id], "skipped": ["missing-id"]}

    delete_resp = client.delete(f"/approvals/{approval_id}")
    assert delete_resp.status_code == 200

    get_resp = client.get(f"/approvals/{approval_id}")
    assert get_resp.status_code == 404
