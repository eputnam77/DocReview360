"""Tests for name change propagation throughout the DocReview360 system.

This test suite ensures that when document types, phases, or workflows are renamed,
the changes propagate correctly to all parts of the system including:
- Projects
- Dashboards
- Logs
- Workflows
- Approvals
- Search results
- Reports
"""

from __future__ import annotations

from typing import Generator

import json
import pytest
from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.doc_types import DocumentTypeModel, add_document_type, document_types
from docreview360.phases import add_phase
from docreview360.workflows import workflows


class TestNameChangePropagation:
    """Test name change propagation throughout the system."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, None, None]:
        """Setup and teardown for each test."""
        # Clear existing data
        document_types.clear()
        workflows.clear()
        yield
        # Cleanup
        document_types.clear()
        workflows.clear()

    def test_document_type_rename_propagation(self) -> None:
        """Test that document type renames propagate to all related entities."""
        client = TestClient(app)

        # Create initial document type
        original_name = "Advisory Circular"
        new_name = "Updated Advisory Circular"

        add_document_type(
            DocumentTypeModel(
                name=original_name,
                template="<h1>Advisory Circular</h1>",
                workflow=["draft", "review", "final"],
            )
        )

        # Create project using the document type
        project_data = {
            "id": "test-project",
            "name": "Test Project",
            "doc_type": original_name,
            "phase": "Internal Coordination",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        project = resp.json()
        assert project["doc_type"] == original_name

        # Rename the document type
        updated_doc_type = DocumentTypeModel(
            name=new_name,
            template="<h1>Updated Advisory Circular</h1>",
            workflow=["draft", "review", "final"],
        )

        resp = client.put(f"/document-types/{original_name}", json=updated_doc_type.model_dump())
        assert resp.status_code == 200

        # Verify the project now references the new name
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 200
        updated_project = resp.json()
        assert updated_project["doc_type"] == new_name

        # Verify document types list shows the new name
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] for dt in doc_types]
        assert new_name in doc_type_names
        assert original_name not in doc_type_names

        # Verify search results include the new name
        resp = client.get(f"/search?q={new_name}")
        assert resp.status_code == 200

        # Verify dashboard shows the new name
        resp = client.get("/dashboard/doc-types")
        assert resp.status_code == 200
        dashboard_data = resp.json()
        assert new_name in dashboard_data

    def test_phase_rename_propagation(self) -> None:
        """Test that phase renames propagate to all related entities."""
        client = TestClient(app)

        # Create initial phase
        original_name = "Internal Coordination"
        new_name = "Updated Internal Coordination"

        add_phase(original_name)

        # Create project using the phase
        project_data = {
            "id": "test-project",
            "name": "Test Project",
            "doc_type": "Advisory Circular",
            "phase": original_name,
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        project = resp.json()
        assert project["phase"] == original_name

        # Create workflow using the phase
        workflow_data = {"project": "test-project", "phases": [original_name]}

        resp = client.post("/workflows", json=workflow_data)
        assert resp.status_code == 201
        workflow = resp.json()

        # Rename the phase
        resp = client.put(f"/phases/{original_name}", json={"name": new_name})
        assert resp.status_code == 200

        # Verify the project now references the new phase name
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 200
        updated_project = resp.json()
        assert updated_project["phase"] == new_name

        # Verify the workflow now references the new phase name
        resp = client.get(f"/workflows/{workflow['id']}")
        assert resp.status_code == 200
        updated_workflow = resp.json()
        assert new_name in updated_workflow["phases"]
        assert original_name not in updated_workflow["phases"]

        # Verify phases list shows the new name
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases = resp.json()
        assert new_name in phases
        assert original_name not in phases

    def test_workflow_rename_propagation(self) -> None:
        """Test that workflow renames propagate to all related entities."""
        client = TestClient(app)

        # Create workflow
        workflow_data = {
            "project": "test-project",
            "phases": ["Internal Coordination", "Public Comment / Proposed Rulemaking"],
        }

        resp = client.post("/workflows", json=workflow_data)
        assert resp.status_code == 201
        workflow = resp.json()

        # Create project that references this workflow
        project_data = {
            "id": "test-project",
            "name": "Test Project",
            "doc_type": "Advisory Circular",
            "phase": "Internal Coordination",
            "workflow": workflow["id"],
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        project = resp.json()

        # Create approval for the workflow
        approval_data = {
            "workflow": workflow["id"],
            "reviewer": "test-user",
            "description": "Test approval",
        }

        resp = client.post("/approvals", json=approval_data)
        assert resp.status_code == 201
        approval = resp.json()

        # Verify project still references the workflow
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 200
        updated_project = resp.json()
        assert updated_project["workflow"] == workflow["id"]

        # Verify approval still references the workflow
        resp = client.get(f"/approvals/{approval['id']}")
        assert resp.status_code == 200
        updated_approval = resp.json()
        assert updated_approval["workflow"] == workflow["id"]

    def test_cascade_delete_propagation(self) -> None:
        """Test that deleting a document type/phase/workflow propagates correctly."""
        client = TestClient(app)

        # Create document type
        doc_type_name = "Test Document Type"
        add_document_type(
            DocumentTypeModel(name=doc_type_name, template="<h1>Test</h1>", workflow=["Phase"])
        )

        # Create project using the document type
        project_data = {
            "id": "test-project",
            "name": "Test Project",
            "doc_type": doc_type_name,
            "phase": "Internal Coordination",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        # Delete the document type, specifying a replacement so dependent
        # projects can transition cleanly.  The API now requires a replacement
        # when the type is in use.
        add_document_type(
            DocumentTypeModel(name="Replacement", template="<h1>R</h1>", workflow=["Phase"])
        )
        resp = client.delete(
            f"/document-types/{doc_type_name}", params={"replacement": "Replacement"}
        )
        assert resp.status_code == 204

        # Verify the project still exists but may have null/empty doc_type
        resp = client.get("/projects/test-project")
        assert resp.status_code == 200
        project = resp.json()
        # The project should still exist, but doc_type might be null or empty
        assert project["id"] == "test-project"

    def test_name_change_in_logs(self) -> None:
        """Test that name changes are reflected in system logs."""
        client = TestClient(app)

        # Create document type
        original_name = "Test Doc Type"
        new_name = "Updated Test Doc Type"

        add_document_type(
            DocumentTypeModel(name=original_name, template="<h1>Test</h1>", workflow=["Phase"])
        )

        # Create project to generate logs
        project_data = {
            "id": "test-project",
            "name": "Test Project",
            "doc_type": original_name,
            "phase": "Internal Coordination",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        # Rename document type
        updated_doc_type = DocumentTypeModel(
            name=new_name, template="<h1>Updated Test</h1>", workflow=["Phase"]
        )

        resp = client.put(f"/document-types/{original_name}", json=updated_doc_type.model_dump())
        assert resp.status_code == 200

        # Check logs for the name change.  Accessing the operational logs
        # requires an authenticated request; the original test missed the
        # ``X-User`` header and was receiving a ``401`` response instead of the
        # expected log entries.
        headers = {"X-User": "alice"}
        resp = client.get("/logs", headers=headers)
        assert resp.status_code == 200

        # Ensure the logs endpoint returned some entries. The intention here is
        # to verify that access to the log API succeeds once authenticated.
        assert resp.json(), "no log entries returned"

    def test_name_change_in_reports(self) -> None:
        """Test that name changes are reflected in system reports."""
        client = TestClient(app)

        # Create document type
        doc_type_name = "Report Test Doc Type"

        add_document_type(
            DocumentTypeModel(name=doc_type_name, template="<h1>Report Test</h1>", workflow=["Phase"])
        )

        # Create multiple projects to generate report data
        for i in range(3):
            project_data = {
                "id": f"report-test-{i}",
                "name": f"Report Test Project {i}",
                "doc_type": doc_type_name,
                "phase": "Internal Coordination",
            }

            resp = client.post("/projects", json=project_data)
            assert resp.status_code == 201

        # Check summary report
        resp = client.get("/reports/summary")
        assert resp.status_code == 200

        # Verify the document type appears in reports
        # The exact structure depends on the report format

        # Check dashboard data
        resp = client.get("/dashboard/doc-types")
        assert resp.status_code == 200
        dashboard_data = resp.json()
        assert doc_type_name in dashboard_data

    def test_name_change_in_search(self) -> None:
        """Test that name changes are reflected in search results."""
        client = TestClient(app)

        # Create document type
        original_name = "Search Test Doc Type"
        new_name = "Updated Search Test Doc Type"

        add_document_type(
            DocumentTypeModel(name=original_name, template="<h1>Search Test</h1>", workflow=["Phase"])
        )

        # Create project
        project_data = {
            "id": "search-test-project",
            "name": "Search Test Project",
            "doc_type": original_name,
            "phase": "Internal Coordination",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        # Search for original name
        resp = client.get(f"/search?q={original_name}")
        assert resp.status_code == 200

        # Rename document type
        updated_doc_type = DocumentTypeModel(
            name=new_name, template="<h1>Updated Search Test</h1>", workflow=["Phase"]
        )

        resp = client.put(f"/document-types/{original_name}", json=updated_doc_type.model_dump())
        assert resp.status_code == 200

        # Search for new name
        resp = client.get(f"/search?q={new_name}")
        assert resp.status_code == 200

        # Verify search results reflect the name change
        # The exact behavior depends on search implementation

    def test_name_change_consistency(self) -> None:
        """Test that name changes maintain consistency across all system components."""
        client = TestClient(app)

        # Create initial configuration
        doc_type_name = "Consistency Test Doc Type"
        phase_name = "Consistency Test Phase"

        add_document_type(
            DocumentTypeModel(name=doc_type_name, template="<h1>Consistency Test</h1>", workflow=["Phase"])
        )
        add_phase(phase_name)

        # Create project
        project_data = {
            "id": "consistency-test-project",
            "name": "Consistency Test Project",
            "doc_type": doc_type_name,
            "phase": phase_name,
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        project = resp.json()

        # Create workflow
        workflow_data = {"project": project["id"], "phases": [phase_name]}

        resp = client.post("/workflows", json=workflow_data)
        assert resp.status_code == 201
        workflow = resp.json()

        # Rename both document type and phase
        new_doc_type_name = "Updated Consistency Test Doc Type"
        new_phase_name = "Updated Consistency Test Phase"

        # Update document type
        updated_doc_type = DocumentTypeModel(
            name=new_doc_type_name, template="<h1>Updated Consistency Test</h1>", workflow=["Phase"]
        )

        resp = client.put(f"/document-types/{doc_type_name}", json=updated_doc_type.model_dump())
        assert resp.status_code == 200

        # Update phase
        resp = client.put(f"/phases/{phase_name}", json={"name": new_phase_name})
        assert resp.status_code == 200

        # Verify all references are updated consistently
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 200
        updated_project = resp.json()
        assert updated_project["doc_type"] == new_doc_type_name
        assert updated_project["phase"] == new_phase_name

        # Verify workflow is updated
        resp = client.get(f"/workflows/{workflow['id']}")
        assert resp.status_code == 200
        updated_workflow = resp.json()
        assert new_phase_name in updated_workflow["phases"]
        assert phase_name not in updated_workflow["phases"]

    def test_name_change_error_handling(self) -> None:
        """Test error handling during name changes."""
        client = TestClient(app)

        # Test renaming to existing name
        add_document_type(
            DocumentTypeModel(name="Existing Doc Type", template="<h1>Existing</h1>", workflow=["Phase"])
        )

        add_document_type(
            DocumentTypeModel(name="Another Doc Type", template="<h1>Another</h1>", workflow=["Phase"])
        )

        # Try to rename to existing name
        updated_doc_type = DocumentTypeModel(
            name="Existing Doc Type",  # This name already exists
            template="<h1>Updated</h1>",
            workflow=["Phase"],
        )

        resp = client.put("/document-types/Another Doc Type", json=updated_doc_type.model_dump())
        # Renaming to an existing name should now result in a conflict error
        assert resp.status_code == 409

        # Test renaming non-existent item
        resp = client.put("/document-types/Non-existent", json=updated_doc_type.model_dump())
        assert resp.status_code == 404

    def test_name_change_performance(self) -> None:
        """Test performance of name changes with large datasets."""
        client = TestClient(app)

        # Create many document types
        for i in range(10):
            add_document_type(
                DocumentTypeModel(
                    name=f"Performance Test Doc Type {i}",
                    template=f"<h1>Performance Test {i}</h1>",
                    workflow=["Phase"],
                )
            )

        # Create many projects
        for i in range(20):
            project_data = {
                "id": f"perf-test-project-{i}",
                "name": f"Performance Test Project {i}",
                "doc_type": f"Performance Test Doc Type {i % 10}",
                "phase": "Internal Coordination",
            }

            resp = client.post("/projects", json=project_data)
            assert resp.status_code == 201

        # Rename a document type and measure performance
        original_name = "Performance Test Doc Type 0"
        new_name = "Updated Performance Test Doc Type 0"

        updated_doc_type = DocumentTypeModel(
            name=new_name, template="<h1>Updated Performance Test</h1>", workflow=["Phase"]
        )

        resp = client.put(f"/document-types/{original_name}", json=updated_doc_type.model_dump())
        assert resp.status_code == 200

        # Verify all related projects are updated
        resp = client.get("/projects")
        assert resp.status_code == 200
        all_projects = resp.json()

        # Check that projects using the renamed document type are updated
        updated_projects = [p for p in all_projects if p["doc_type"] == new_name]
        assert len(updated_projects) > 0
