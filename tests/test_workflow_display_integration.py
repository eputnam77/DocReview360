"""Integration tests to ensure workflows appear in project details page after creation/editing."""

from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient

from docreview360 import doc_types
from docreview360.api import app
from docreview360.doc_types import DocumentTypeModel, add_document_type
from docreview360.phases import _phases, add_phase
from docreview360.workflows import create_workflow, workflows


class TestWorkflowDisplayIntegration:
    """Test that workflows selected during creation/editing appear in project details."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, None, None]:
        """Setup and teardown for each test."""
        # Clear existing data
        doc_types.document_types.clear()
        _phases.clear()
        workflows.clear()

        # Add test configuration
        add_document_type(
            DocumentTypeModel(
                name="Test Document Type",
                template="<h1>Test Template</h1>",
                workflow=["draft", "review", "approve"],
            )
        )

        add_phase("Test Phase 1")
        add_phase("Test Phase 2")
        add_phase("Test Phase 3")

        # Create test workflows
        create_workflow("test-workflow-1", ["Test Phase 1", "Test Phase 2"])
        create_workflow("test-workflow-2", ["Test Phase 1", "Test Phase 2", "Test Phase 3"])

        yield

        # Cleanup
        doc_types.document_types.clear()
        _phases.clear()
        workflows.clear()

    def test_workflow_appears_in_project_details_after_creation(self) -> None:
        """Test that workflow selected during project creation appears in project details page."""
        client = TestClient(app)

        # Create project with workflow
        project_data = {
            "id": "test-project-1",
            "name": "Test Project with Workflow",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "test-workflow-1",
            "user": "test-user",
            "description": "Test project description",
        }

        # Create project
        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        project = resp.json()
        assert project["workflow"] is not None
        workflow_id = project["workflow"]

        # Verify workflow exists
        wf_resp = client.get(f"/workflows/{workflow_id}")
        assert wf_resp.status_code == 200
        workflow = wf_resp.json()
        assert workflow["project"] == "test-project-1"

        # Verify project details page shows the workflow
        project_resp = client.get(f"/projects/{project['id']}")
        assert project_resp.status_code == 200
        project_details = project_resp.json()
        assert project_details["workflow"] == workflow_id

        # Verify workflow steps are available for display
        assert "phases" in workflow or "steps" in workflow

    def test_workflow_appears_in_project_details_after_editing(self) -> None:
        """Test that workflow selected during project editing appears in project details page."""
        client = TestClient(app)

        # Create initial project without workflow
        initial_project_data = {
            "id": "test-project-2",
            "name": "Test Project for Editing",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "user": "test-user",
            "description": "Initial project description",
        }

        resp = client.post("/projects", json=initial_project_data)
        assert resp.status_code == 201

        initial_project = resp.json()
        assert initial_project["workflow"] is None

        # Edit project to add workflow
        edit_data = {"workflow": "test-workflow-2"}

        edit_resp = client.put(f"/projects/{initial_project['id']}", json=edit_data)
        assert edit_resp.status_code == 200

        updated_project = edit_resp.json()
        assert updated_project["workflow"] is not None
        workflow_id = updated_project["workflow"]

        # Verify workflow exists and is linked to project
        wf_resp = client.get(f"/workflows/{workflow_id}")
        assert wf_resp.status_code == 200
        workflow = wf_resp.json()
        assert workflow["project"] == "test-project-2"

        # Verify project details page shows the updated workflow
        project_resp = client.get(f"/projects/{initial_project['id']}")
        assert project_resp.status_code == 200
        project_details = project_resp.json()
        assert project_details["workflow"] == workflow_id

    def test_workflow_change_appears_in_project_details_after_editing(self) -> None:
        """Test that changing workflow during editing appears in project details page."""
        client = TestClient(app)

        # Create project with initial workflow
        initial_project_data = {
            "id": "test-project-3",
            "name": "Test Project for Workflow Change",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "test-workflow-1",
            "user": "test-user",
            "description": "Project with initial workflow",
        }

        resp = client.post("/projects", json=initial_project_data)
        assert resp.status_code == 201

        initial_project = resp.json()
        initial_workflow_id = initial_project["workflow"]

        # Verify initial workflow
        wf_resp = client.get(f"/workflows/{initial_workflow_id}")
        assert wf_resp.status_code == 200
        initial_workflow = wf_resp.json()
        assert initial_workflow["project"] == "test-project-3"

        # Edit project to change workflow
        edit_data = {"workflow": "test-workflow-2"}

        edit_resp = client.put(f"/projects/{initial_project['id']}", json=edit_data)
        assert edit_resp.status_code == 200

        updated_project = edit_resp.json()
        new_workflow_id = updated_project["workflow"]
        assert new_workflow_id != initial_workflow_id

        # Verify new workflow exists and is linked to project
        wf_resp = client.get(f"/workflows/{new_workflow_id}")
        assert wf_resp.status_code == 200
        new_workflow = wf_resp.json()
        assert new_workflow["project"] == "test-project-3"

        # Verify the previous workflow is no longer linked to the project
        old_wf_resp = client.get(f"/workflows/{initial_workflow_id}")
        assert old_wf_resp.status_code == 200
        old_workflow = old_wf_resp.json()
        assert old_workflow["project"] == ""

        # Verify project details page shows the new workflow
        project_resp = client.get(f"/projects/{initial_project['id']}")
        assert project_resp.status_code == 200
        project_details = project_resp.json()
        assert project_details["workflow"] == new_workflow_id

        project_workflow_resp = client.get(f"/projects/{initial_project['id']}/workflow")
        assert project_workflow_resp.status_code == 200
        project_workflow = project_workflow_resp.json()
        assert project_workflow["id"] == new_workflow_id

    def test_workflow_approvals_appear_in_project_details(self) -> None:
        """Test that workflow approvals appear in project details page."""
        client = TestClient(app)

        # Create project with workflow
        project_data = {
            "id": "test-project-4",
            "name": "Test Project with Approvals",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "test-workflow-1",
            "user": "test-user",
            "description": "Test project with approvals",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        project = resp.json()
        workflow_id = project["workflow"]

        # Create approvals for the workflow
        approval_data = {"workflow": workflow_id, "reviewer": "reviewer1@example.com"}

        approval_resp = client.post("/approvals", json=approval_data)
        assert approval_resp.status_code == 201

        # Verify approvals are linked to the workflow
        approvals_resp = client.get(f"/approvals?workflow={workflow_id}")
        assert approvals_resp.status_code == 200
        approvals = approvals_resp.json()
        assert len(approvals) > 0
        assert any(a["workflow"] == workflow_id for a in approvals)

    def test_workflow_phase_mapping_persistence(self) -> None:
        """Test that phase-workflow mapping persists through project lifecycle."""
        client = TestClient(app)

        # Create project with phase and workflow mapping
        project_data = {
            "id": "test-project-5",
            "name": "Test Project with Phase Mapping",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "test-workflow-1",
            "user": "test-user",
            "description": "Test project with phase mapping",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        project = resp.json()

        # Verify phase and workflow are correctly associated
        assert project["phase"] == "Test Phase 1"
        assert project["workflow"] is not None

        # Edit project to change phase
        edit_data = {"phase": "Test Phase 2"}

        edit_resp = client.put(f"/projects/{project['id']}", json=edit_data)
        assert edit_resp.status_code == 200

        updated_project = edit_resp.json()
        assert updated_project["phase"] == "Test Phase 2"

        # Verify workflow association is maintained
        assert updated_project["workflow"] is not None

    def test_workflow_removal_from_project(self) -> None:
        """Test that removing workflow from project is reflected in details page."""
        client = TestClient(app)

        # Create project with workflow
        project_data = {
            "id": "test-project-6",
            "name": "Test Project for Workflow Removal",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "test-workflow-1",
            "user": "test-user",
            "description": "Project for workflow removal test",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        project = resp.json()
        assert project["workflow"] is not None

        # Remove workflow from project
        edit_data = {"workflow": None}

        edit_resp = client.put(f"/projects/{project['id']}", json=edit_data)
        assert edit_resp.status_code == 200

        updated_project = edit_resp.json()
        assert updated_project["workflow"] is None

        # Verify project details page shows no workflow
        project_resp = client.get(f"/projects/{project['id']}")
        assert project_resp.status_code == 200
        project_details = project_resp.json()
        assert project_details["workflow"] is None

        workflow_resp = client.get(f"/workflows/{project['workflow']}")
        assert workflow_resp.status_code == 200
        workflow_details = workflow_resp.json()
        assert workflow_details["project"] == ""

        project_workflow_resp = client.get(f"/projects/{project['id']}/workflow")
        assert project_workflow_resp.status_code == 404

    def test_workflow_display_consistency_across_endpoints(self) -> None:
        """Test that workflow information is consistent across all project endpoints."""
        client = TestClient(app)

        # Create project with workflow
        project_data = {
            "id": "test-project-7",
            "name": "Test Project for Consistency",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "test-workflow-1",
            "user": "test-user",
            "description": "Project for consistency testing",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        project = resp.json()
        workflow_id = project["workflow"]

        # Verify workflow ID is consistent across endpoints
        project_resp = client.get(f"/projects/{project['id']}")
        assert project_resp.status_code == 200
        project_details = project_resp.json()
        assert project_details["workflow"] == workflow_id

        # Verify workflow details are accessible
        wf_resp = client.get(f"/workflows/{workflow_id}")
        assert wf_resp.status_code == 200
        workflow = wf_resp.json()
        assert workflow["project"] == project["id"]

        # Verify project appears in workflow's project list
        projects_resp = client.get("/projects")
        assert projects_resp.status_code == 200
        projects_list = projects_resp.json()
        project_in_list = next((p for p in projects_list if p["id"] == project["id"]), None)
        assert project_in_list is not None
        assert project_in_list["workflow"] == workflow_id
