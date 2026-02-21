from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.workflows import workflows


def _admin_headers() -> dict[str, str]:
    auth.USER_REPOSITORY.create_user(
        "alice",
        auth.DEMO_USER_DEFAULTS["alice"]["password"],
        otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
    )
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"})
    return {"Authorization": f"Bearer {token}"}


def test_project_creation_links_workflow() -> None:
    client = TestClient(app)
    headers = _admin_headers()
    workflows.clear()
    resp = client.post(
        "/projects",
        json={"id": "p100", "name": "WF Test", "workflow": "review"},
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["workflow"]
    assert wf_id in workflows
    wf_resp = client.get(f"/workflows/{wf_id}", headers=headers)
    assert wf_resp.status_code == 200
    assert wf_resp.json()["project"] == "p100"


def test_workflow_appears_in_project_details_after_creation() -> None:
    """Test that workflow selected during project creation appears in project details page."""
    client = TestClient(app)
    headers = _admin_headers()
    workflows.clear()

    # Create project with workflow
    resp = client.post(
        "/projects",
        json={"id": "p101", "name": "WF Display Test", "workflow": "review"},
        headers=headers,
    )
    assert resp.status_code == 201

    project = resp.json()
    workflow_id = project["workflow"]
    assert workflow_id is not None

    # Verify workflow exists and is linked to project
    wf_resp = client.get(f"/workflows/{workflow_id}", headers=headers)
    assert wf_resp.status_code == 200
    workflow = wf_resp.json()
    assert workflow["project"] == "p101"

    # Verify project details page shows the workflow
    project_resp = client.get(f"/projects/{project['id']}", headers=headers)
    assert project_resp.status_code == 200
    project_details = project_resp.json()
    assert project_details["workflow"] == workflow_id


def test_workflow_appears_in_project_details_after_editing() -> None:
    """Test that workflow selected during project editing appears in project details page."""
    client = TestClient(app)
    headers = _admin_headers()
    workflows.clear()

    # Create initial project without workflow
    resp = client.post(
        "/projects",
        json={"id": "p102", "name": "WF Edit Test"},
        headers=headers,
    )
    assert resp.status_code == 201

    initial_project = resp.json()
    assert initial_project["workflow"] is None

    # Edit project to add workflow
    edit_resp = client.put(
        f"/projects/{initial_project['id']}",
        json={"workflow": "review"},
        headers=headers,
    )
    assert edit_resp.status_code == 200

    updated_project = edit_resp.json()
    workflow_id = updated_project["workflow"]
    assert workflow_id is not None

    # Verify workflow exists and is linked to project
    wf_resp = client.get(f"/workflows/{workflow_id}", headers=headers)
    assert wf_resp.status_code == 200
    workflow = wf_resp.json()
    assert workflow["project"] == "p102"

    # Verify project details page shows the updated workflow
    project_resp = client.get(f"/projects/{initial_project['id']}", headers=headers)
    assert project_resp.status_code == 200
    project_details = project_resp.json()
    assert project_details["workflow"] == workflow_id


def test_projects_can_share_same_workflow_template() -> None:
    client = TestClient(app)
    headers = _admin_headers()
    workflows.clear()

    first = client.post(
        "/projects",
        json={"id": "p103", "name": "WF Shared A", "workflow": "review"},
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/projects",
        json={"id": "p104", "name": "WF Shared B", "workflow": "review"},
        headers=headers,
    )
    assert second.status_code == 201

    first_wf_id = first.json()["workflow"]
    second_wf_id = second.json()["workflow"]

    assert first_wf_id != second_wf_id

    first_wf = client.get(f"/workflows/{first_wf_id}", headers=headers)
    second_wf = client.get(f"/workflows/{second_wf_id}", headers=headers)
    assert first_wf.status_code == 200
    assert second_wf.status_code == 200
    assert first_wf.json()["project"] == "p103"
    assert second_wf.json()["project"] == "p104"
    assert first_wf.json()["template"] == second_wf.json()["template"]


def test_edit_project_assigns_new_workflow_instance_for_template_reuse() -> None:
    client = TestClient(app)
    headers = _admin_headers()
    workflows.clear()

    first = client.post(
        "/projects",
        json={"id": "p105", "name": "WF Edit Shared A", "workflow": "review"},
        headers=headers,
    )
    assert first.status_code == 201
    first_wf_id = first.json()["workflow"]

    second = client.post(
        "/projects",
        json={"id": "p106", "name": "WF Edit Shared B"},
        headers=headers,
    )
    assert second.status_code == 201

    update = client.put("/projects/p106", json={"workflow": "review"}, headers=headers)
    assert update.status_code == 200

    second_wf_id = update.json()["workflow"]
    assert second_wf_id
    assert second_wf_id != first_wf_id

    first_wf = client.get(f"/workflows/{first_wf_id}", headers=headers)
    second_wf = client.get(f"/workflows/{second_wf_id}", headers=headers)
    assert first_wf.status_code == 200
    assert second_wf.status_code == 200
    assert first_wf.json()["project"] == "p105"
    assert second_wf.json()["project"] == "p106"
    assert first_wf.json()["template"] == second_wf.json()["template"]
