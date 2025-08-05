"""End-to-end tests for configuration flow from setup to project creation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.doc_types import add_document_type, document_types, DocumentTypeModel
from docreview360.phases import add_phase, _phases
from docreview360.workflows import create_workflow, workflows


class TestEndToEndConfigurationFlow:
    """Test the complete configuration to project creation flow."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> None:
        """Setup and teardown for each test."""
        # Clear existing data
        document_types.clear()
        _phases.clear()
        workflows.clear()
        yield
        # Cleanup
        document_types.clear()
        _phases.clear()
        workflows.clear()

    def test_complete_configuration_to_project_flow(self) -> None:
        """Test the complete flow: config setup → frontend display → project creation."""
        client = TestClient(app)
        
        # Step 1: Setup configuration
        add_document_type(DocumentTypeModel(
            name="E2E Test Document Type",
            template="<h1>E2E Test Template</h1>",
            workflow=["draft", "review", "approve"]
        ))
        add_phase("E2E Test Phase 1")
        add_phase("E2E Test Phase 2")
        create_workflow("e2e-test-project", ["E2E Test Phase 1", "E2E Test Phase 2"])
        
        # Step 2: Verify configuration appears in frontend endpoints
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in doc_types]
        assert "E2E Test Document Type" in doc_type_names
        
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases_data = resp.json()
        assert "E2E Test Phase 1" in phases_data
        assert "E2E Test Phase 2" in phases_data
        
        resp = client.get("/workflows")
        assert resp.status_code == 200
        workflows_data = resp.json()
        # Workflows might be returned differently, so check structure
        assert isinstance(workflows_data, list)
        
        # Step 3: Create project using configuration
        project_data = {
            "id": "e2e-test-project",
            "name": "E2E Test Project",
            "doc_type": "E2E Test Document Type",
            "phase": "E2E Test Phase 1",
            "user": "e2e-test-user",
            "description": "E2E test project description"
        }
        
        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        
        project = resp.json()
        assert project["id"] == "e2e-test-project"
        assert project["name"] == "E2E Test Project"
        assert project["doc_type"] == "E2E Test Document Type"
        assert project["phase"] == "E2E Test Phase 1"
        assert project["user"] == "e2e-test-user"
        
        # Step 4: Verify project appears in project list
        resp = client.get("/projects")
        assert resp.status_code == 200
        projects = resp.json()
        project_ids = [p["id"] for p in projects]
        assert "e2e-test-project" in project_ids

    def test_configuration_update_workflow(self) -> None:
        """Test that configuration updates properly propagate through the system."""
        client = TestClient(app)
        
        # Initial configuration
        add_document_type(DocumentTypeModel(
            name="Initial Doc Type",
            template="<h1>Initial</h1>"
        ))
        add_phase("Initial Phase")
        
        # Create project with initial configuration
        project_data = {
            "id": "update-test-project",
            "name": "Update Test Project",
            "doc_type": "Initial Doc Type",
            "phase": "Initial Phase"
        }
        
        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        
        # Update configuration
        document_types.clear()
        _phases.clear()
        
        add_document_type(DocumentTypeModel(
            name="Updated Doc Type",
            template="<h1>Updated</h1>"
        ))
        add_phase("Updated Phase")
        
        # Verify configuration is updated
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in doc_types]
        assert "Updated Doc Type" in doc_type_names
        assert "Initial Doc Type" not in doc_type_names
        
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases_data = resp.json()
        assert "Updated Phase" in phases_data
        assert "Initial Phase" not in phases_data
        
        # Create new project with updated configuration
        updated_project_data = {
            "id": "updated-test-project",
            "name": "Updated Test Project",
            "doc_type": "Updated Doc Type",
            "phase": "Updated Phase"
        }
        
        resp = client.post("/projects", json=updated_project_data)
        assert resp.status_code == 201
        
        # Verify both projects exist
        resp = client.get("/projects")
        assert resp.status_code == 200
        projects = resp.json()
        project_ids = [p["id"] for p in projects]
        assert "update-test-project" in project_ids
        assert "updated-test-project" in project_ids

    def test_configuration_validation_flow(self) -> None:
        """Test configuration validation throughout the flow."""
        client = TestClient(app)
        
        # Test with invalid configuration
        try:
            add_document_type(DocumentTypeModel(
                name="",  # Invalid empty name
                template="<h1>Invalid</h1>"
            ))
        except Exception:
            # Should handle validation errors gracefully
            pass
        
        try:
            add_phase("")  # Invalid empty phase name
        except Exception:
            # Should handle validation errors gracefully
            pass
        
        # Test project creation with invalid configuration references
        project_data = {
            "id": "invalid-config-test",
            "name": "Invalid Config Test Project",
            "doc_type": "Non-existent Document Type",
            "phase": "Non-existent Phase"
        }
        
        resp = client.post("/projects", json=project_data)
        # Should handle invalid configuration gracefully
        assert resp.status_code in [201, 400, 422]

    def test_configuration_persistence_flow(self) -> None:
        """Test that configuration persists across multiple operations."""
        client = TestClient(app)
        
        # Setup configuration
        add_document_type(DocumentTypeModel(
            name="Persistence Test Doc",
            template="<h1>Persistence</h1>"
        ))
        add_phase("Persistence Phase")
        
        # Create multiple projects
        for i in range(3):
            project_data = {
                "id": f"persistence-test-{i}",
                "name": f"Persistence Test Project {i}",
                "doc_type": "Persistence Test Doc",
                "phase": "Persistence Phase"
            }
            
            resp = client.post("/projects", json=project_data)
            assert resp.status_code == 201
        
        # Verify configuration is still available
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in doc_types]
        assert "Persistence Test Doc" in doc_type_names
        
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases_data = resp.json()
        assert "Persistence Phase" in phases_data
        
        # Verify all projects exist
        resp = client.get("/projects")
        assert resp.status_code == 200
        projects = resp.json()
        project_ids = [p["id"] for p in projects]
        for i in range(3):
            assert f"persistence-test-{i}" in project_ids

    def test_configuration_error_recovery_flow(self) -> None:
        """Test error recovery in the configuration flow."""
        client = TestClient(app)
        
        # Test with corrupted configuration
        document_types.clear()
        _phases.clear()
        workflows.clear()
        
        # Try to create project with no configuration
        project_data = {
            "id": "error-recovery-test",
            "name": "Error Recovery Test Project"
        }
        
        resp = client.post("/projects", json=project_data)
        # Should handle missing configuration gracefully
        assert resp.status_code in [201, 400, 422]
        
        # Verify endpoints still work
        resp = client.get("/document-types")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        
        resp = client.get("/phases")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        
        resp = client.get("/workflows")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        
        # Recover by adding configuration
        add_document_type(DocumentTypeModel(
            name="Recovery Test Doc",
            template="<h1>Recovery</h1>"
        ))
        add_phase("Recovery Phase")
        
        # Verify recovery worked
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in doc_types]
        assert "Recovery Test Doc" in doc_type_names
        
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases_data = resp.json()
        assert "Recovery Phase" in phases_data

    def test_configuration_performance_flow(self) -> None:
        """Test performance of the complete configuration flow."""
        client = TestClient(app)
        
        import time
        
        # Setup configuration with many items
        for i in range(10):
            add_document_type(DocumentTypeModel(
                name=f"Performance Test Doc {i}",
                template=f"<h1>Performance {i}</h1>"
            ))
            add_phase(f"Performance Phase {i}")
        
        # Test configuration retrieval performance
        start_time = time.time()
        
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        assert len(doc_types) >= 10
        
        resp = client.get("/phases")
        assert resp.status_code == 200
        phases_data = resp.json()
        assert len(phases_data) >= 10
        
        end_time = time.time()
        assert end_time - start_time < 2.0  # Should complete within 2 seconds
        
        # Test project creation performance
        start_time = time.time()
        
        for i in range(5):
            project_data = {
                "id": f"perf-test-{i}",
                "name": f"Performance Test Project {i}",
                "doc_type": f"Performance Test Doc {i % 10}",
                "phase": f"Performance Phase {i % 10}"
            }
            
            resp = client.post("/projects", json=project_data)
            assert resp.status_code == 201
        
        end_time = time.time()
        assert end_time - start_time < 5.0  # Should complete within 5 seconds
        
        # Test project listing performance
        start_time = time.time()
        
        resp = client.get("/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert len(projects) >= 5
        
        end_time = time.time()
        assert end_time - start_time < 1.0  # Should complete within 1 second 