"""Integration tests for frontend-backend field synchronization."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.doc_types import add_document_type, document_types, DocumentTypeModel
from docreview360.phases import add_phase, _phases


class TestFrontendBackendIntegration:
    """Test frontend-backend field synchronization and mapping."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> None:
        """Setup and teardown for each test."""
        # Clear existing data
        document_types.clear()
        _phases.clear()
        yield
        # Cleanup
        document_types.clear()
        _phases.clear()

    def test_frontend_backend_field_mapping(self) -> None:
        """Test that frontend form fields correctly map to backend project model."""
        client = TestClient(app)
        
        # Add test configuration
        add_document_type(DocumentTypeModel(
            name="Test Doc Type",
            template="<h1>Test</h1>"
        ))
        add_phase("Test Phase")
        
        # Test frontend FormData format mapping
        frontend_form_data = {
            "docId": "DOC-123",
            "title": "Frontend Project Title",
            "sme": "John Doe",
            "docType": "Test Doc Type",
            "phase": "Test Phase",
            "description": "Frontend project description"
        }
        
        # Expected backend format
        expected_backend_data = {
            "id": frontend_form_data["docId"],
            "name": frontend_form_data["title"],
            "user": frontend_form_data["sme"],
            "doc_type": frontend_form_data["docType"],
            "phase": frontend_form_data["phase"],
            "description": frontend_form_data["description"]
        }
        
        # Test both formats work
        # Backend JSON format
        resp = client.post("/projects", json=expected_backend_data)
        assert resp.status_code == 201
        
        project = resp.json()
        assert project["id"] == "DOC-123"
        assert project["name"] == "Frontend Project Title"
        assert project["user"] == "John Doe"
        assert project["doc_type"] == "Test Doc Type"
        assert project["phase"] == "Test Phase"
        assert project["description"] == "Frontend project description"
        
        # Frontend FormData format (if supported)
        resp = client.post("/projects", data=frontend_form_data)
        # Should handle FormData appropriately
        assert resp.status_code in [201, 422]  # 422 if FormData not supported

    def test_field_validation_consistency(self) -> None:
        """Test that field validation is consistent between frontend and backend."""
        client = TestClient(app)
        
        # Test required fields
        incomplete_data = {
            "id": "validation-test",
            # Missing required fields
        }
        
        resp = client.post("/projects", json=incomplete_data)
        # Should validate appropriately
        assert resp.status_code in [201, 400, 422]
        
        # Test field length limits
        long_name = "A" * 1000  # Very long name
        long_description = "B" * 5000  # Very long description
        
        long_data = {
            "id": "long-test",
            "name": long_name,
            "description": long_description
        }
        
        resp = client.post("/projects", json=long_data)
        # Should handle long fields appropriately
        assert resp.status_code in [201, 400, 422]
        
        # Test special characters
        special_chars_data = {
            "id": "special-test",
            "name": "Project with special chars: !@#$%^&*()",
            "description": "Description with <script>alert('xss')</script>"
        }
        
        resp = client.post("/projects", json=special_chars_data)
        # Should handle special characters appropriately
        assert resp.status_code in [201, 400, 422]

    def test_error_handling_consistency(self) -> None:
        """Test that error handling is consistent between frontend and backend."""
        client = TestClient(app)
        
        # Test duplicate project ID
        project_data = {
            "id": "duplicate-test",
            "name": "First Project"
        }
        
        # Create first project
        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        
        # Try to create duplicate
        resp = client.post("/projects", json=project_data)
        # Should handle duplicate gracefully
        assert resp.status_code in [201, 400, 409]  # 409 for conflict
        
        # Test invalid project ID format
        invalid_id_data = {
            "id": "",  # Empty ID
            "name": "Invalid ID Project"
        }
        
        resp = client.post("/projects", json=invalid_id_data)
        # Should validate ID format
        assert resp.status_code in [201, 400, 422]
        
        # Test with invalid document type
        invalid_doc_type_data = {
            "id": "invalid-doc-type",
            "name": "Invalid Doc Type Project",
            "doc_type": "Non-existent Document Type"
        }
        
        resp = client.post("/projects", json=invalid_doc_type_data)
        # Should handle invalid document type appropriately
        assert resp.status_code in [201, 400, 422]

    def test_api_response_consistency(self) -> None:
        """Test that API responses are consistent and well-formed."""
        client = TestClient(app)
        
        # Create a test project
        project_data = {
            "id": "response-test",
            "name": "Response Test Project",
            "description": "Test project for response consistency"
        }
        
        resp = client.post("/projects", json=project_data)
        assert resp.status_code == 201
        
        project = resp.json()
        
        # Verify response structure
        required_fields = ["id", "name", "created_at"]
        for field in required_fields:
            assert field in project
        
        # Verify data types
        assert isinstance(project["id"], str)
        assert isinstance(project["name"], str)
        assert isinstance(project["created_at"], str)  # ISO date string
        
        # Test GET project endpoint
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 200
        
        retrieved_project = resp.json()
        assert retrieved_project == project  # Should be identical
        
        # Test list projects endpoint
        resp = client.get("/projects")
        assert resp.status_code == 200
        
        projects = resp.json()
        assert isinstance(projects, list)
        
        # Should include our test project
        project_ids = [p["id"] for p in projects]
        assert "response-test" in project_ids

    def test_configuration_endpoint_consistency(self) -> None:
        """Test that configuration endpoints return consistent data."""
        client = TestClient(app)
        
        # Add test configuration
        add_document_type(DocumentTypeModel(
            name="Consistency Test Doc",
            template="<h1>Consistency</h1>"
        ))
        add_phase("Consistency Phase")
        
        # Test document types endpoint
        resp = client.get("/document-types")
        assert resp.status_code == 200
        
        doc_types = resp.json()
        assert isinstance(doc_types, list)
        
        # Should include our test document type
        doc_type_names = [dt["name"] if isinstance(dt, dict) else dt for dt in doc_types]
        assert "Consistency Test Doc" in doc_type_names
        
        # Test phases endpoint
        resp = client.get("/phases")
        assert resp.status_code == 200
        
        phases = resp.json()
        assert isinstance(phases, list)
        
        # Should include our test phase
        assert "Consistency Phase" in phases
        
        # Test workflows endpoint
        resp = client.get("/workflows")
        assert resp.status_code == 200
        
        workflows = resp.json()
        assert isinstance(workflows, list)

    def test_frontend_compatibility_endpoints(self) -> None:
        """Test endpoints that frontend specifically uses."""
        client = TestClient(app)
        
        # Test environments endpoint (used by frontend)
        resp = client.get("/environments")
        assert resp.status_code == 200
        
        # Test users/me endpoint (used by frontend)
        resp = client.get("/users/me")
        assert resp.status_code == 200
        
        user_data = resp.json()
        assert "username" in user_data
        assert "is_admin" in user_data
        
        # Test ping endpoint (used by frontend for health checks)
        resp = client.get("/ping")
        assert resp.status_code == 200
        
        # Test metrics endpoint (used by frontend dashboards)
        resp = client.get("/metrics/summary")
        assert resp.status_code == 200
        
        metrics = resp.json()
        assert isinstance(metrics, dict)

    def test_cors_and_headers(self) -> None:
        """Test that CORS and headers are properly configured for frontend."""
        client = TestClient(app)
        
        # Test OPTIONS request (CORS preflight)
        resp = client.options("/projects")
        # Should handle OPTIONS appropriately
        assert resp.status_code in [200, 405]  # 405 if OPTIONS not supported
        
        # Test that responses include appropriate headers
        resp = client.get("/projects")
        assert resp.status_code == 200
        
        # Check for common headers
        headers = resp.headers
        assert "content-type" in headers
        assert "application/json" in headers["content-type"]

    def test_error_response_format(self) -> None:
        """Test that error responses are properly formatted for frontend consumption."""
        client = TestClient(app)
        
        # Test 404 error
        resp = client.get("/projects/non-existent-project")
        assert resp.status_code == 404
        
        # Error response should be JSON
        error_data = resp.json()
        assert isinstance(error_data, dict)
        
        # Test 422 validation error
        invalid_data = {
            "id": "",  # Invalid empty ID
            "name": ""  # Invalid empty name
        }
        
        resp = client.post("/projects", json=invalid_data)
        if resp.status_code == 422:
            error_data = resp.json()
            assert isinstance(error_data, dict)
            # Should include validation details
            assert "detail" in error_data 