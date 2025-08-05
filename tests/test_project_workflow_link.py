from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.workflows import workflows


def test_project_creation_links_workflow() -> None:
    client = TestClient(app)
    workflows.clear()
    resp = client.post(
        "/projects",
        json={"id": "p100", "name": "WF Test", "workflow": "review"},
    )
    assert resp.status_code == 201
    wf_id = resp.json()["workflow"]
    assert wf_id in workflows
    wf_resp = client.get(f"/workflows/{wf_id}")
    assert wf_resp.status_code == 200
    assert wf_resp.json()["project"] == "p100"
