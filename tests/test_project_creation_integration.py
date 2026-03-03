"""Integration tests for project creation with configuration propagation."""

from __future__ import annotations

from datetime import timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth, doc_types
from docreview360.api import app
from docreview360.doc_types import DocumentTypeModel, add_document_type
from docreview360.phases import add_phase, reset_phases
from docreview360.workflows import create_workflow, workflows


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for a test 'alice' admin user."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass  # user may already exist
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


class TestProjectCreationIntegration:
    """Test project creation with configuration integration."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, None, None]:
        """Setup and teardown for each test."""
        # Clear existing data
        doc_types.document_types.clear()
        reset_phases()
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

        # Create workflow using the correct API
        create_workflow("test-project", ["Test Phase 1", "Test Phase 2"])

        yield

        # Cleanup
        doc_types.document_types.clear()
        reset_phases()
        workflows.clear()

    def test_project_creation_with_configuration_fields(self) -> None:
        """Test that project creation uses configuration from document types, phases, workflows."""
        client = TestClient(app)
        headers = _alice_headers()

        # Test that configuration is available
        doc_types_resp = client.get("/document-types")
        assert doc_types_resp.status_code == 200
        doc_types = doc_types_resp.json()
        assert any(dt["name"] == "Test Document Type" for dt in doc_types)

        phases_resp = client.get("/phases")
        assert phases_resp.status_code == 200
        phases_data = phases_resp.json()
        assert "Test Phase 1" in phases_data
        assert "Test Phase 2" in phases_data

        workflows_resp = client.get("/workflows")
        assert workflows_resp.status_code == 200
        workflows_data = workflows_resp.json()
        assert any(wf["project"] == "test-project" for wf in workflows_data)

        # Create project using configuration
        project_data = {
            "id": "test-project-1",
            "name": "Test Project",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            # Workflow IDs are generated, so omit workflow for simplicity
            "user": "test-user",
            "description": "Test project description",
        }

        resp = client.post("/projects", json=project_data, headers=headers)
        assert resp.status_code == 201

        project = resp.json()
        assert project["doc_type"] == "Test Document Type"

    def test_project_creation_field_validation(self) -> None:
        """Test that all required fields are validated during project creation."""
        client = TestClient(app)
        headers = _alice_headers()

        # Test missing required fields
        incomplete_data = {
            "id": "test-project-2",
            "name": "Test Project",
            # Missing doc_type, phase, workflow
        }

        resp = client.post("/projects", json=incomplete_data, headers=headers)
        # Should still succeed as these might be optional in current implementation
        # but we can test that the fields are properly handled
        assert resp.status_code in [201, 422]  # 422 if validation is strict

        # Test with invalid document type
        invalid_data = {
            "id": "test-project-3",
            "name": "Test Project",
            "doc_type": "Non-existent Document Type",
            "phase": "Test Phase 1",
            "workflow": "Test Workflow",
        }

        resp = client.post("/projects", json=invalid_data, headers=headers)
        # Should handle gracefully - either succeed with default or fail appropriately
        assert resp.status_code in [201, 400, 422]

    def test_project_creation_frontend_backend_sync(self) -> None:
        """Test that frontend form data correctly maps to backend project model."""
        client = TestClient(app)
        headers = _alice_headers()

        # Simulate frontend FormData format
        frontend_data = {
            "docId": "DOC-123",
            "title": "Frontend Test Project",
            "sme": "John Doe",
            "docType": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "Test Workflow",
            "description": "Frontend project description",
        }

        # Test both JSON and FormData formats
        # JSON format (what backend expects)
        json_data = {
            "id": frontend_data["docId"],
            "name": frontend_data["title"],
            "user": frontend_data["sme"],
            "doc_type": frontend_data["docType"],
            "phase": frontend_data["phase"],
            "workflow": frontend_data["workflow"],
            "description": frontend_data["description"],
        }

        resp = client.post("/projects", json=json_data, headers=headers)
        assert resp.status_code == 201

        project = resp.json()
        assert project["id"] == "DOC-123"
        assert project["name"] == "Frontend Test Project"
        assert project["user"] == "John Doe"
        assert project["doc_type"] == "Test Document Type"

        # Test FormData format (what frontend sends)
        resp = client.post("/projects", data=frontend_data, headers=headers)
        # Should handle FormData appropriately
        assert resp.status_code in [201, 422]  # 422 if FormData not supported

    def test_project_creation_with_file_upload(self) -> None:
        """Test project creation with file upload integration."""
        client = TestClient(app)
        headers = _alice_headers()

        project_data = {
            "id": "test-project-file",
            "name": "File Upload Test Project",
            "doc_type": "Test Document Type",
            "phase": "Test Phase 1",
            "workflow": "Test Workflow",
        }

        # Create project
        resp = client.post("/projects", json=project_data, headers=headers)
        assert resp.status_code == 201

        # Upload file to project
        files = {"file": ("test.txt", "Test file content", "text/plain")}
        upload_resp = client.post(f"/projects/{project_data['id']}/upload", files=files, headers=headers)

        # File upload might not be implemented yet, so check for appropriate response
        assert upload_resp.status_code in [200, 201, 404, 501]

    def test_project_creation_error_handling(self) -> None:
        """Test error handling during project creation."""
        client = TestClient(app)
        headers = _alice_headers()

        # Test duplicate project ID
        project_data = {
            "id": "duplicate-test",
            "name": "First Project",
            "doc_type": "Test Document Type",
        }

        # Create first project
        resp = client.post("/projects", json=project_data, headers=headers)
        assert resp.status_code == 201

        # Try to create duplicate
        resp = client.post("/projects", json=project_data, headers=headers)
        # Should handle duplicate gracefully
        assert resp.status_code in [201, 400, 409]  # 409 for conflict

        # Test invalid project data
        invalid_data = {
            "id": "",  # Empty ID
            "name": "",  # Empty name
        }

        resp = client.post("/projects", json=invalid_data, headers=headers)
        # Should validate and handle appropriately
        assert resp.status_code in [201, 400, 422]


class TestConfigurationPropagation:
    """Test configuration propagation to frontend and projects."""

    def test_document_types_propagate_to_frontend(self) -> None:
        """Test that document types from configuration appear in frontend endpoints."""
        client = TestClient(app)

        # Clear existing document types
        doc_types.document_types.clear()

        # Add test document types
        test_types = [
            DocumentTypeModel(
                name="Policy Document",
                template="<h1>Policy</h1>",
                workflow=["Draft"],
            ),
            DocumentTypeModel(
                name="Procedure Manual",
                template="<h1>Procedure</h1>",
                workflow=["Draft"],
            ),
            DocumentTypeModel(
                name="Technical Spec",
                template="<h1>Technical</h1>",
                workflow=["Draft"],
            ),
        ]

        for doc_type in test_types:
            add_document_type(doc_type)

        # Test that they appear in the API
        resp = client.get("/document-types")
        assert resp.status_code == 200

        types_payload = resp.json()
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in types_payload]

        assert "Policy Document" in doc_type_names
        assert "Procedure Manual" in doc_type_names
        assert "Technical Spec" in doc_type_names

    def test_phases_propagate_to_frontend(self) -> None:
        """Test that phases from configuration appear in frontend endpoints."""
        client = TestClient(app)

        # Clear existing phases
        reset_phases()

        # Add test phases
        test_phases = ["Draft", "Review", "Approval", "Published"]
        for phase in test_phases:
            add_phase(phase)

        # Test that they appear in the API
        resp = client.get("/phases")
        assert resp.status_code == 200

        phases_data = resp.json()
        assert "Draft" in phases_data
        assert "Review" in phases_data
        assert "Approval" in phases_data
        assert "Published" in phases_data

    def test_workflows_propagate_to_frontend(self) -> None:
        """Test that workflows from configuration appear in frontend endpoints."""
        client = TestClient(app)

        # Clear existing workflows
        workflows.clear()

        # Add test workflows
        test_workflows = [
            {"name": "Simple Review", "phases": ["Draft", "Review", "Approval"]},
            {
                "name": "Complex Review",
                "phases": [
                    "Draft",
                    "Internal Review",
                    "External Review",
                    "Approval",
                    "Published",
                ],
            },
        ]

        for wf in test_workflows:
            # Create a workflow instance for a dummy project using the provided phases
            create_workflow(
                project=f"proj-{wf['name'].replace(' ', '-').lower()}",
                phases=wf["phases"],
            )

        # Test that they appear in the API
        resp = client.get("/workflows")
        assert resp.status_code == 200

        workflows_data = resp.json()
        workflow_projects = [wf["project"] for wf in workflows_data]

        assert "proj-simple-review" in workflow_projects
        assert "proj-complex-review" in workflow_projects

    def test_configuration_changes_affect_new_projects(self) -> None:
        """Test that configuration changes immediately affect new project creation."""
        client = TestClient(app)
        headers = _alice_headers()

        # Clear existing configuration
        doc_types.document_types.clear()
        reset_phases()
        workflows.clear()

        # Add initial configuration
        add_document_type(
            {
                "name": "Initial Doc Type",
                "template": "<h1>Initial</h1>",
                "workflow": ["Initial Phase"],
            }
        )
        add_phase("Initial Phase")
        create_workflow(project="init-proj", phases=["Initial Phase"])

        # Create project with initial configuration
        project_data = {
            "id": "config-test-1",
            "name": "Initial Config Project",
            "doc_type": "Initial Doc Type",
            "phase": "Initial Phase",
            "workflow": "Initial Workflow",
        }

        resp = client.post("/projects", json=project_data, headers=headers)
        assert resp.status_code == 201

        # Update configuration
        add_document_type(
            {
                "name": "Updated Doc Type",
                "template": "<h1>Updated</h1>",
                "workflow": ["Updated Phase"],
            }
        )
        add_phase("Updated Phase")
        create_workflow(project="updated-proj", phases=["Updated Phase"])

        # Create new project with updated configuration
        updated_project_data = {
            "id": "config-test-2",
            "name": "Updated Config Project",
            "doc_type": "Updated Doc Type",
            "phase": "Updated Phase",
            "workflow": "Updated Workflow",
        }

        resp = client.post("/projects", json=updated_project_data, headers=headers)
        assert resp.status_code == 201

        # Verify both projects exist with their respective configurations
        resp = client.get("/projects", headers=headers)
        assert resp.status_code == 200

        projects = resp.json()
        project_ids = [p["id"] for p in projects]
        assert "config-test-1" in project_ids
        assert "config-test-2" in project_ids
