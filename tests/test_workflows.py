from docreview360.api import app
from fastapi.testclient import TestClient


def test_workflow_lifecycle() -> None:
    client = TestClient(app)
    resp = client.post(
        "/workflows",
        json={"project": "p1", "phases": ["draft", "review", "done"]},
    )
    assert resp.status_code == 201
    wf = resp.json()
    wf_id = wf["id"]
    assert wf["phase"] == "draft"

    resp = client.post(f"/workflows/{wf_id}/assign", json={"user": "alice"})
    assert resp.status_code == 200
    assert resp.json()["reviewers"] == ["alice"]

    resp = client.post(f"/workflows/{wf_id}/advance")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "review"
