from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _create_workflow(client: TestClient, project_id: str) -> str:
    hdrs = _alice_headers()
    resp = client.post(
        "/workflows",
        json={"project": project_id, "phases": ["draft", "approval"]},
        headers=hdrs,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_approval(client: TestClient, wf_id: str, reviewer: str = "alice") -> str:
    hdrs = _alice_headers()
    resp = client.post(
        "/approvals",
        json={
            "workflow": wf_id,
            "reviewer": reviewer,
            "doc_id": wf_id,
        },
        headers=hdrs,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_approval_reminders_and_deletion() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    workflow_id = _create_workflow(client, "proj-remind")
    approval_id = _create_approval(client, workflow_id)

    reminder_resp = client.post(
        "/approvals/remind",
        json={"ids": [approval_id, "missing-id"]},
        headers=hdrs,
    )
    assert reminder_resp.status_code == 200
    assert reminder_resp.json() == {"sent": [approval_id], "skipped": ["missing-id"]}

    delete_resp = client.delete(f"/approvals/{approval_id}", headers=hdrs)
    assert delete_resp.status_code == 200

    get_resp = client.get(f"/approvals/{approval_id}", headers=hdrs)
    assert get_resp.status_code == 404
