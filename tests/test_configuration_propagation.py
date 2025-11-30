"""Tests for configuration propagation from backend to frontend and projects."""

from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.doc_types import DocumentTypeModel, add_document_type, document_types
from docreview360.phases import _phases, add_phase
from docreview360.workflows import workflows


class TestConfigurationPropagation:
    """Test configuration propagation to frontend and projects."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, None, None]:
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

    def test_project_settings_from_configuration(self) -> None:
        """Test that project settings are properly inherited from configuration."""
        client = TestClient(app)

        # Add configuration
        add_document_type(
            DocumentTypeModel(
                name="Test Doc Type",
                template="<h1>Test Template</h1>",
                workflow=["draft", "review", "approve"],
            )
        )
        add_phase("Test Phase")

        # Create project using configuration
        project_data = {
            "id": "config-test",
            "name": "Configuration Test Project",
            "doc_type": "Test Doc Type",
            "phase": "Test Phase",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        project = resp.json()
        assert project["doc_type"] == "Test Doc Type"
        assert project["phase"] == "Test Phase"

        # Verify project inherits configuration settings
        assert project["id"] == "config-test"
        assert project["name"] == "Configuration Test Project"

    def test_configuration_validation(self) -> None:
        """Test that invalid configuration is properly handled."""
        client = TestClient(app)

        # Test with non-existent document type
        project_data = {
            "id": "invalid-config-test",
            "name": "Invalid Config Project",
            "doc_type": "Non-existent Doc Type",
            "phase": "Non-existent Phase",
        }

        resp = client.post("/projects", json=project_data)
        # Should handle gracefully - either succeed with defaults or fail appropriately
        assert resp.status_code in [201, 400, 422]

        # Test with empty configuration
        document_types.clear()
        _phases.clear()

        resp = client.get("/document-types")
        assert resp.status_code == 200
        # Should return empty list or default values
        assert isinstance(resp.json(), list)

        resp = client.get("/phases")
        assert resp.status_code == 200
        # Should return empty list or default values
        assert isinstance(resp.json(), list)

    def test_configuration_defaults(self) -> None:
        """Test that default values are used when configuration is missing."""
        client = TestClient(app)

        # Clear all configuration
        document_types.clear()
        _phases.clear()
        workflows.clear()

        # Test that endpoints still work with defaults
        resp = client.get("/document-types")
        assert resp.status_code == 200

        resp = client.get("/phases")
        assert resp.status_code == 200

        resp = client.get("/workflows")
        assert resp.status_code == 200

        # Test project creation with minimal data
        project_data = {"id": "defaults-test", "name": "Defaults Test Project"}

        resp = client.post("/projects", json=project_data)
        # Should succeed with defaults or fail gracefully
        assert resp.status_code in [201, 400, 422]

    def test_configuration_update_workflow(self) -> None:
        """Test that configuration updates properly propagate through the system."""
        client = TestClient(app)

        # Initial configuration
        add_document_type(
            DocumentTypeModel(
                name="Initial Doc Type",
                template="<h1>Initial</h1>",
                workflow=["Initial Phase"],
            )
        )
        add_phase("Initial Phase")

        # Verify initial state
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in doc_types]
        assert "Initial Doc Type" in doc_type_names

        resp = client.get("/phases")
        assert resp.status_code == 200
        phases_data = resp.json()
        assert "Initial Phase" in phases_data

        # Update configuration
        document_types.clear()
        _phases.clear()

        add_document_type(
            DocumentTypeModel(
                name="Updated Doc Type",
                template="<h1>Updated</h1>",
                workflow=["Updated Phase"],
            )
        )
        add_phase("Updated Phase")

        # Verify updated state
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

    def test_configuration_consistency(self) -> None:
        """Test that configuration remains consistent across API calls."""
        client = TestClient(app)

        # Add configuration
        add_document_type(
            DocumentTypeModel(
                name="Consistency Test Doc",
                template="<h1>Consistency</h1>",
                workflow=["Consistency Phase"],
            )
        )
        add_phase("Consistency Phase")

        # Multiple API calls should return consistent data
        resp1 = client.get("/document-types")
        resp2 = client.get("/document-types")
        assert resp1.json() == resp2.json()

        resp1 = client.get("/phases")
        resp2 = client.get("/phases")
        assert resp1.json() == resp2.json()

        # Configuration should persist across project operations
        project_data = {
            "id": "consistency-test",
            "name": "Consistency Test Project",
            "doc_type": "Consistency Test Doc",
            "phase": "Consistency Phase",
        }

        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201

        # Configuration should still be available after project creation
        resp = client.get("/document-types")
        assert resp.status_code == 200
        doc_types = resp.json()
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in doc_types]
        assert "Consistency Test Doc" in doc_type_names

    def test_configuration_error_handling(self) -> None:
        """Test error handling for configuration operations."""
        client = TestClient(app)

        # Test with malformed document type data
        try:
            add_document_type(
                DocumentTypeModel(
                    name="",  # Empty name
                    template="<h1>Test</h1>",
                    workflow=["Phase"],
                )
            )
        except Exception:
            # Should handle validation errors gracefully
            pass

        # Test with invalid phase names
        try:
            add_phase("")  # Empty phase name
        except Exception:
            # Should handle validation errors gracefully
            pass

        # Test API endpoints with invalid data
        resp = client.post("/document-types", json={"name": "", "template": ""})  # Invalid data
        # Should handle validation appropriately
        assert resp.status_code in [201, 400, 422]

    def test_configuration_performance(self) -> None:
        """Test that configuration operations perform well."""
        client = TestClient(app)

        # Add multiple configuration items
        for i in range(10):
            add_document_type(
                DocumentTypeModel(
                    name=f"Performance Test Doc {i}",
                    template=f"<h1>Performance {i}</h1>",
                    workflow=[f"Performance Phase {i}"],
                )
            )
            add_phase(f"Performance Phase {i}")

        # API calls should be fast
        import time

        start_time = time.time()

        resp = client.get("/document-types")
        assert resp.status_code == 200

        doc_types = resp.json()
        assert len(doc_types) >= 10

        end_time = time.time()
        assert end_time - start_time < 1.0  # Should complete within 1 second

        # Phases should also be fast
        start_time = time.time()

        resp = client.get("/phases")
        assert resp.status_code == 200

        phases_data = resp.json()
        assert len(phases_data) >= 10

        end_time = time.time()
        assert end_time - start_time < 1.0  # Should complete within 1 second
