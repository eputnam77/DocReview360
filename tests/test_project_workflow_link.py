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


def test_workflow_appears_in_project_details_after_creation() -> None:
    """Test that workflow selected during project creation appears in project details page."""
    client = TestClient(app)
    workflows.clear()

    # Create project with workflow
    resp = client.post(
        "/projects",
        json={"id": "p101", "name": "WF Display Test", "workflow": "review"},
    )
    assert resp.status_code == 201

    project = resp.json()
    workflow_id = project["workflow"]
    assert workflow_id is not None

    # Verify workflow exists and is linked to project
    wf_resp = client.get(f"/workflows/{workflow_id}")
    assert wf_resp.status_code == 200
    workflow = wf_resp.json()
    assert workflow["project"] == "p101"

    # Verify project details page shows the workflow
    project_resp = client.get(f"/projects/{project['id']}")
    assert project_resp.status_code == 200
    project_details = project_resp.json()
    assert project_details["workflow"] == workflow_id


def test_workflow_appears_in_project_details_after_editing() -> None:
    """Test that workflow selected during project editing appears in project details page."""
    client = TestClient(app)
    workflows.clear()

    # Create initial project without workflow
    resp = client.post(
        "/projects",
        json={"id": "p102", "name": "WF Edit Test"},
    )
    assert resp.status_code == 201

    initial_project = resp.json()
    assert initial_project["workflow"] is None

    # Edit project to add workflow
    edit_resp = client.put(
        f"/projects/{initial_project['id']}",
        json={"workflow": "review"}
    )
    assert edit_resp.status_code == 200

    updated_project = edit_resp.json()
    workflow_id = updated_project["workflow"]
    assert workflow_id is not None

    # Verify workflow exists and is linked to project
    wf_resp = client.get(f"/workflows/{workflow_id}")
    assert wf_resp.status_code == 200
    workflow = wf_resp.json()
    assert workflow["project"] == "p102"

    # Verify project details page shows the updated workflow
    project_resp = client.get(f"/projects/{initial_project['id']}")
    assert project_resp.status_code == 200
    project_details = project_resp.json()
    assert project_details["workflow"] == workflow_id
