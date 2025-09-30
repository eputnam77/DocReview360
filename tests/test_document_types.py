from fastapi.testclient import TestClient
import pytest

from docreview360.api import app
from docreview360.doc_types import (
    DocumentTypeModel,
    add_document_type,
    document_types,
    export_document_types,
    import_document_types_json,
    list_all_phases,
)


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
        name="Test Document Type", template="", workflow=["Seed"]
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


def test_idempotent_add() -> None:
    """Adding the same document type twice should be a no-op."""
    doc = DocumentTypeModel(name="Duplicate", template="<h1>Dup</h1>", workflow=["Phase"])
    first = add_document_type(doc)
    second = add_document_type(doc)
    assert first is second
    assert document_types["Duplicate"].template == "<h1>Dup</h1>"


def test_conflicting_add() -> None:
    """Adding a type with the same name but different data should error."""
    add_document_type(
        DocumentTypeModel(name="Conflict", template="<h1>One</h1>", workflow=["Phase"])
    )
    with pytest.raises(ValueError):
        add_document_type(
            DocumentTypeModel(name="Conflict", template="<h1>Two</h1>", workflow=["Phase"])
        )


def test_export_error(tmp_path):
    dest_dir = tmp_path / "dir"
    dest_dir.mkdir()
    with pytest.raises(ValueError):
        export_document_types(dest_dir)


def test_import_document_types_json_error() -> None:
    with pytest.raises(ValueError):
        import_document_types_json("{}")


def test_list_all_phases() -> None:
    phases = list_all_phases()
    assert isinstance(phases, list)


def test_document_type_import_export_endpoints() -> None:
    client = TestClient(app)

    data = {"name": "policy", "template": "<h1>Policy</h1>", "workflow": ["Phase"]}
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
