from fastapi.testclient import TestClient
import pytest

from docreview360.api import app
from docreview360.doc_types import DocumentTypeModel, document_types


@pytest.fixture(autouse=True)
def _reset_doc_types() -> None:
    """Start each test with a single seeded document type.

    Many tests mutate the global ``document_types`` registry without
    resetting it which causes later tests to observe leftover types.  The
    CRUD tests expect only the application's default seed to remain after
    deleting their temporary type.  We therefore clear the registry and add
    back a single "Test Document Type" before each test.
    """

    document_types.clear()
    document_types["Test Document Type"] = DocumentTypeModel(
        name="Test Document Type", template=""
    )


def test_document_type_crud() -> None:
    client = TestClient(app)
    data = {
        "name": "policy",
        "template": "<h1>Policy</h1>",
        "workflow": ["review", "approve"],
    }
    resp = client.post("/document-types", json=data)
    assert resp.status_code == 201
    resp = client.get("/document-types")
    assert resp.status_code == 200
    names = {d["name"] for d in resp.json()}
    assert "policy" in names
    resp = client.get("/document-types/policy")
    assert resp.status_code == 200
    assert resp.json()["workflow"] == ["review", "approve"]

    updated = data | {"template": "<h1>Updated</h1>"}
    resp = client.put("/document-types/policy", json=updated)
    assert resp.status_code == 200
    assert resp.json()["template"] == "<h1>Updated</h1>"

    resp = client.delete("/document-types/policy")
    assert resp.status_code == 204
    resp = client.get("/document-types")
    names = {d["name"] for d in resp.json()}
    # The application seeds a default document type used across tests.
    # Recent updates renamed this seed to "Test Document Type", so the
    # final state after CRUD operations should reflect that default.
    assert names == {"Test Document Type"}


def test_document_type_import_export_endpoints() -> None:
    client = TestClient(app)

    data = {"name": "policy", "template": "<h1>Policy</h1>"}
    resp = client.post("/document-types", json=data)
    assert resp.status_code == 201

    export_resp = client.get("/document-types/export")
    assert export_resp.status_code == 200
    payload = export_resp.text

    resp = client.delete("/document-types/policy")
    assert resp.status_code == 204

    import_resp = client.post(
        "/document-types/import",
        files={"file": ("types.json", payload, "application/json")},
    )
    assert import_resp.status_code == 201

    names = {d["name"] for d in import_resp.json()}
    assert "policy" in names
