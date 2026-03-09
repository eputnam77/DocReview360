"""Tests for replacement deletion functionality.

This test suite ensures that when document types, phases, or workflows are deleted
while they are in use, the system properly requires replacement selection and
handles the replacement process correctly.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth, doc_types, rbac
from docreview360.api import app
from docreview360.doc_types import DocumentTypeModel, add_document_type
from docreview360.phases import add_phase
from docreview360.search import ProjectModel, add_project, projects
from docreview360.workflows import workflows


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
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


class TestReplacementDeletion:
    """Test replacement deletion functionality."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, None, None]:
        """Setup and teardown for each test."""
        # Clear existing data
        doc_types.document_types.clear()
        workflows.clear()
        projects.clear()
        yield
        # Cleanup
        doc_types.document_types.clear()
        workflows.clear()
        projects.clear()

    def test_document_type_usage_check(self) -> None:
        """Test that document type usage is correctly detected."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create document types
        add_document_type(
            DocumentTypeModel(
                name="Test Doc Type 1", template="<h1>Test 1</h1>", workflow=["Phase"]
            )
        )
        add_document_type(
            DocumentTypeModel(
                name="Test Doc Type 2", template="<h1>Test 2</h1>", workflow=["Phase"]
            )
        )

        # Create project using the document type
        project = ProjectModel(id="test-project", name="Test Project", doc_type="Test Doc Type 1")
        add_project(project)

        # Check usage
        resp = client.get("/document-types/Test Doc Type 1/usage", headers=hdrs)
        assert resp.status_code == 200
        usage = resp.json()

        assert usage["name"] == "Test Doc Type 1"
        assert usage["in_use"] is True
        assert usage["usage_count"] == 1
        assert len(usage["projects"]) == 1
        assert usage["projects"][0]["id"] == "test-project"
        assert usage["projects"][0]["name"] == "Test Project"

        # Check unused document type
        resp = client.get("/document-types/Test Doc Type 2/usage", headers=hdrs)
        assert resp.status_code == 200
        usage = resp.json()

        assert usage["name"] == "Test Doc Type 2"
        assert usage["in_use"] is False
        assert usage["usage_count"] == 0
        assert len(usage["projects"]) == 0

    def test_document_type_delete_with_replacement(self) -> None:
        """Test document type deletion with replacement."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create document types
        add_document_type(
            DocumentTypeModel(
                name="Original Doc Type", template="<h1>Original</h1>", workflow=["Phase"]
            )
        )
        add_document_type(
            DocumentTypeModel(
                name="Replacement Doc Type", template="<h1>Replacement</h1>", workflow=["Phase"]
            )
        )

        # Create project using the original document type
        project = ProjectModel(id="test-project", name="Test Project", doc_type="Original Doc Type")
        add_project(project)

        # Try to delete without replacement (should fail)
        resp = client.delete("/document-types/Original Doc Type", headers=hdrs)
        assert resp.status_code == 400
        error = resp.json()
        assert "is in use" in error["detail"]
        assert "Please specify a replacement" in error["detail"]

        # Delete with replacement
        resp = client.delete(
            "/document-types/Original Doc Type?replacement=Replacement Doc Type", headers=hdrs
        )
        assert resp.status_code == 204

        # Verify the project now uses the replacement
        resp = client.get("/projects/test-project", headers=hdrs)
        assert resp.status_code == 200
        updated_project = resp.json()
        assert updated_project["doc_type"] == "Replacement Doc Type"

        # Verify original document type is deleted
        resp = client.get("/document-types", headers=hdrs)
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] for dt in doc_types]
        assert "Original Doc Type" not in doc_type_names
        assert "Replacement Doc Type" in doc_type_names

    def test_document_type_delete_without_replacement(self) -> None:
        """Test document type deletion when not in use (no replacement needed)."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create document type
        add_document_type(
            DocumentTypeModel(
                name="Unused Doc Type", template="<h1>Unused</h1>", workflow=["Phase"]
            )
        )

        # Delete without replacement (should succeed)
        resp = client.delete("/document-types/Unused Doc Type", headers=hdrs)
        assert resp.status_code == 204

        # Verify document type is deleted
        resp = client.get("/document-types", headers=hdrs)
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] for dt in doc_types]
        assert "Unused Doc Type" not in doc_type_names

    def test_document_type_delete_invalid_replacement(self) -> None:
        """Test document type deletion with invalid replacement."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create document type
        add_document_type(
            DocumentTypeModel(name="Test Doc Type", template="<h1>Test</h1>", workflow=["Phase"])
        )

        # Create project using the document type
        project = ProjectModel(id="test-project", name="Test Project", doc_type="Test Doc Type")
        add_project(project)

        # Try to delete with non-existent replacement
        resp = client.delete("/document-types/Test Doc Type?replacement=Non-existent Doc Type", headers=hdrs)
        assert resp.status_code == 404
        error = resp.json()
        assert "Replacement document type 'Non-existent Doc Type' not found" in error["detail"]

    def test_phase_usage_check(self) -> None:
        """Test that phase usage is correctly detected."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create phases
        add_phase("Test Phase 1")
        add_phase("Test Phase 2")

        # Create project (phases are used through workflows)
        project = ProjectModel(id="test-project", name="Test Project", workflow="test-workflow")
        add_project(project)

        # Create workflow using the phase
        workflow_data = {"project": "test-project", "phases": ["Test Phase 1"]}
        resp = client.post("/workflows", json=workflow_data, headers=_alice_headers())
        assert resp.status_code == 201

        # Check usage
        resp = client.get("/phases/Test Phase 1/usage", headers=hdrs)
        assert resp.status_code == 200
        usage = resp.json()

        assert usage["name"] == "Test Phase 1"
        assert usage["in_use"] is True
        assert usage["usage_count"] >= 1  # At least 1 workflow uses it

        # Check unused phase
        resp = client.get("/phases/Test Phase 2/usage", headers=hdrs)
        assert resp.status_code == 200
        usage = resp.json()

        assert usage["name"] == "Test Phase 2"
        assert usage["in_use"] is False
        assert usage["usage_count"] == 0

    def test_phase_delete_with_replacement(self) -> None:
        """Test phase deletion with replacement."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create phases
        add_phase("Original Phase")
        add_phase("Replacement Phase")

        # Create workflow using the original phase
        workflow_data = {"project": "test-project", "phases": ["Original Phase"]}
        resp = client.post("/workflows", json=workflow_data, headers=hdrs)
        assert resp.status_code == 201

        # Try to delete without replacement (should fail)
        resp = client.delete("/phases/Original Phase", headers=hdrs)
        assert resp.status_code == 400
        error = resp.json()
        assert "is in use" in error["detail"]
        assert "Please specify a replacement" in error["detail"]

        # Delete with replacement
        resp = client.delete("/phases/Original Phase?replacement=Replacement Phase", headers=hdrs)
        assert resp.status_code == 204

        # Verify original phase is deleted
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases = resp.json()
        assert "Original Phase" not in phases
        assert "Replacement Phase" in phases

    def test_phase_delete_without_replacement(self) -> None:
        """Test phase deletion when not in use (no replacement needed)."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create phase
        add_phase("Unused Phase")

        # Delete without replacement (should succeed)
        resp = client.delete("/phases/Unused Phase", headers=hdrs)
        assert resp.status_code == 204

        # Verify phase is deleted
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases = resp.json()
        assert "Unused Phase" not in phases

    def test_phase_delete_invalid_replacement(self) -> None:
        """Test phase deletion with invalid replacement."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create phase
        add_phase("Test Phase")

        # Create workflow using the phase
        workflow_data = {"project": "test-project", "phases": ["Test Phase"]}
        resp = client.post("/workflows", json=workflow_data, headers=hdrs)
        assert resp.status_code == 201

        # Try to delete with non-existent replacement
        resp = client.delete("/phases/Test Phase?replacement=Non-existent Phase", headers=hdrs)
        assert resp.status_code == 404
        error = resp.json()
        assert "Replacement phase 'Non-existent Phase' not found" in error["detail"]

    def test_delete_nonexistent_item(self) -> None:
        """Test deletion of non-existent items."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Try to delete non-existent document type
        resp = client.delete("/document-types/Non-existent Doc Type", headers=hdrs)
        assert resp.status_code == 404

        # Try to delete non-existent phase
        resp = client.delete("/phases/Non-existent Phase", headers=hdrs)
        assert resp.status_code == 404

    def test_multiple_projects_affected(self) -> None:
        """Test that multiple projects are properly updated when replacement is selected."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create document types
        add_document_type(
            DocumentTypeModel(
                name="Original Doc Type", template="<h1>Original</h1>", workflow=["Phase"]
            )
        )
        add_document_type(
            DocumentTypeModel(
                name="Replacement Doc Type", template="<h1>Replacement</h1>", workflow=["Phase"]
            )
        )

        # Create multiple projects using the original document type
        for i in range(3):
            project = ProjectModel(
                id=f"test-project-{i}", name=f"Test Project {i}", doc_type="Original Doc Type"
            )
            add_project(project)

        # Delete with replacement
        resp = client.delete(
            "/document-types/Original Doc Type?replacement=Replacement Doc Type", headers=hdrs
        )
        assert resp.status_code == 204

        # Verify all projects now use the replacement
        for i in range(3):
            resp = client.get(f"/projects/test-project-{i}", headers=hdrs)
            assert resp.status_code == 200
            updated_project = resp.json()
            assert updated_project["doc_type"] == "Replacement Doc Type"

    def test_usage_check_nonexistent_item(self) -> None:
        """Test usage check for non-existent items."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Check usage for non-existent document type
        resp = client.get("/document-types/Non-existent Doc Type/usage", headers=hdrs)
        assert resp.status_code == 404

        # Check usage for non-existent phase
        resp = client.get("/phases/Non-existent Phase/usage", headers=hdrs)
        assert resp.status_code == 404

    def test_replacement_validation(self) -> None:
        """Test that replacement validation works correctly."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create document type
        add_document_type(
            DocumentTypeModel(name="Test Doc Type", template="<h1>Test</h1>", workflow=["Phase"])
        )

        # Create project using the document type
        project = ProjectModel(id="test-project", name="Test Project", doc_type="Test Doc Type")
        add_project(project)

        # Try to replace with the same document type (should fail)
        resp = client.delete("/document-types/Test Doc Type?replacement=Test Doc Type", headers=hdrs)
        assert resp.status_code == 400
        error = resp.json()
        assert "Replacement document type 'Test Doc Type' not found" in error["detail"]

    def test_cascade_effects(self) -> None:
        """Test that deletion with replacement properly cascades to all affected entities."""
        client = TestClient(app)
        hdrs = _alice_headers()

        # Create document types
        add_document_type(
            DocumentTypeModel(
                name="Original Doc Type", template="<h1>Original</h1>", workflow=["Phase"]
            )
        )
        add_document_type(
            DocumentTypeModel(
                name="Replacement Doc Type", template="<h1>Replacement</h1>", workflow=["Phase"]
            )
        )

        # Create project
        project = ProjectModel(id="test-project", name="Test Project", doc_type="Original Doc Type")
        add_project(project)

        # Verify initial state
        resp = client.get("/projects/test-project", headers=hdrs)
        assert resp.status_code == 200
        original_project = resp.json()
        assert original_project["doc_type"] == "Original Doc Type"

        # Delete with replacement
        resp = client.delete(
            "/document-types/Original Doc Type?replacement=Replacement Doc Type", headers=hdrs
        )
        assert resp.status_code == 204

        # Verify project is updated
        resp = client.get("/projects/test-project", headers=hdrs)
        assert resp.status_code == 200
        updated_project = resp.json()
        assert updated_project["doc_type"] == "Replacement Doc Type"

        # Verify document types list is updated
        resp = client.get("/document-types", headers=hdrs)
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] for dt in doc_types]
        assert "Original Doc Type" not in doc_type_names
        assert "Replacement Doc Type" in doc_type_names
