from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app


def _admin_headers() -> dict[str, str]:
    auth.USER_REPOSITORY.create_user(
        "alice",
        auth.DEMO_USER_DEFAULTS["alice"]["password"],
        otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
    )
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"})
    return {"Authorization": f"Bearer {token}"}


def _ensure_user(client: TestClient, username: str, headers: dict[str, str]) -> None:
    resp = client.post(
        "/users",
        json={"username": username, "roles": ["reviewer"], "active": True},
        headers=headers,
    )
    assert resp.status_code in {201, 409}


def test_project_reviewer_crud_updates_assignments() -> None:
    client = TestClient(app)
    headers = _admin_headers()
    _ensure_user(client, "alice", headers)
    _ensure_user(client, "bob", headers)

    wf_resp = client.post(
        "/workflows",
        json={"project": "proj-reviewers", "phases": ["draft", "review"]},
        headers=headers,
    )
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    project_resp = client.post(
        "/projects",
        json={"id": "proj-reviewers", "name": "Reviewer Project", "workflow": wf_id},
        headers=headers,
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    add_resp = client.post(
        f"/projects/{project_id}/reviewers",
        json={"reviewer": "alice"},
        headers=headers,
    )
    assert add_resp.status_code == 200
    assert "alice" in add_resp.json()

    project = client.get(f"/projects/{project_id}", headers=headers).json()
    assert "alice" in project["reviewers"]

    approvals = client.get(f"/approvals?workflow={wf_id}", headers=headers).json()
    assert any(a["reviewer"] == "alice" for a in approvals)

    assigned = client.get("/projects", params={"user": "alice"}, headers=headers).json()
    assert any(p["id"] == project_id for p in assigned)

    update_resp = client.put(
        f"/projects/{project_id}/reviewers/alice",
        json={"reviewer": "bob"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert "bob" in update_resp.json()
    approvals = client.get(f"/approvals?workflow={wf_id}", headers=headers).json()
    assert any(a["reviewer"] == "bob" for a in approvals)
    assert not any(a["reviewer"] == "alice" for a in approvals)

    delete_resp = client.delete(f"/projects/{project_id}/reviewers/bob", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json() == []
    approvals = client.get(f"/approvals?workflow={wf_id}", headers=headers).json()
    assert not any(a["reviewer"] == "bob" for a in approvals)
