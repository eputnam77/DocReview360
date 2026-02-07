from fastapi.testclient import TestClient

from docreview360.api import app


def _ensure_user(client: TestClient, username: str) -> None:
    resp = client.post(
        "/users",
        json={"username": username, "roles": ["reviewer"], "active": True},
    )
    assert resp.status_code in {201, 409}


def test_project_reviewer_crud_updates_assignments() -> None:
    client = TestClient(app)
    _ensure_user(client, "alice")
    _ensure_user(client, "bob")

    wf_resp = client.post(
        "/workflows",
        json={"project": "proj-reviewers", "phases": ["draft", "review"]},
    )
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    project_resp = client.post(
        "/projects",
        json={"id": "proj-reviewers", "name": "Reviewer Project", "workflow": wf_id},
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    add_resp = client.post(
        f"/projects/{project_id}/reviewers",
        json={"reviewer": "alice"},
    )
    assert add_resp.status_code == 200
    assert "alice" in add_resp.json()

    project = client.get(f"/projects/{project_id}").json()
    assert "alice" in project["reviewers"]

    approvals = client.get(f"/approvals?workflow={wf_id}").json()
    assert any(a["reviewer"] == "alice" for a in approvals)

    assigned = client.get("/projects", params={"user": "alice"}).json()
    assert any(p["id"] == project_id for p in assigned)

    update_resp = client.put(
        f"/projects/{project_id}/reviewers/alice",
        json={"reviewer": "bob"},
    )
    assert update_resp.status_code == 200
    assert "bob" in update_resp.json()
    approvals = client.get(f"/approvals?workflow={wf_id}").json()
    assert any(a["reviewer"] == "bob" for a in approvals)
    assert not any(a["reviewer"] == "alice" for a in approvals)

    delete_resp = client.delete(f"/projects/{project_id}/reviewers/bob")
    assert delete_resp.status_code == 200
    assert delete_resp.json() == []
    approvals = client.get(f"/approvals?workflow={wf_id}").json()
    assert not any(a["reviewer"] == "bob" for a in approvals)
