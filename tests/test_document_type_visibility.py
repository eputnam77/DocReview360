from __future__ import annotations

from fastapi.testclient import TestClient

from docreview360 import doc_types
from docreview360.api import app
from docreview360.search import projects


def test_document_types_visible_across_admin_projects_dashboard(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "doc_types.json")
    doc_types.document_types.clear()
    projects.clear()

    create_payload = {"name": "Admin Doc", "template": "", "workflow": []}
    response = client.post("/document-types", json=create_payload)
    assert response.status_code == 201
    assert (tmp_path / "doc_types.json").exists()

    replacement_payload = {"name": "Replacement Doc", "template": "", "workflow": []}
    response = client.post("/document-types", json=replacement_payload)
    assert response.status_code == 201

    project_payload = {"id": "doc-type-project", "name": "Doc Type Project", "doc_type": "Admin Doc"}
    response = client.post("/projects", json=project_payload)
    assert response.status_code == 201

    doc_types_response = client.get("/document-types")
    assert doc_types_response.status_code == 200
    doc_type_names = {doc_type["name"] for doc_type in doc_types_response.json()}
    assert {"Admin Doc", "Replacement Doc"} <= doc_type_names

    dashboard_response = client.get("/dashboard/doc-types")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json() == {"Admin Doc": 1}

    rename_payload = {"name": "Admin Doc Renamed", "template": "", "workflow": []}
    response = client.put("/document-types/Admin Doc", json=rename_payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Admin Doc Renamed"

    dashboard_response = client.get("/dashboard/doc-types")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json() == {"Admin Doc Renamed": 1}

    response = client.delete(
        "/document-types/Admin Doc Renamed",
        params={"replacement": "Replacement Doc"},
    )
    assert response.status_code == 204

    project_response = client.get("/projects/doc-type-project")
    assert project_response.status_code == 200
    assert project_response.json()["doc_type"] == "Replacement Doc"

    doc_types_response = client.get("/document-types")
    doc_type_names = {doc_type["name"] for doc_type in doc_types_response.json()}
    assert "Admin Doc Renamed" not in doc_type_names
    assert "Replacement Doc" in doc_type_names

    dashboard_response = client.get("/dashboard/doc-types")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json() == {"Replacement Doc": 1}
