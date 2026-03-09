"""Tests for document type CRUD (DB-backed)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.doc_types import (
    DocumentTypeModel,
    add_document_type,
    export_document_types,
    import_document_types_json,
    list_all_phases,
    reset_document_types,
)


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset_doc_types() -> None:
    """Start each test with a single seeded document type (DB-backed)."""
    reset_document_types(seed=False)
    add_document_type(DocumentTypeModel(name="Test Document Type", template="", workflow=["Seed"]))
    yield
    reset_document_types(seed=False)


def test_document_type_crud() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    data = {
        "name": "policy",
        "template": "<h1>Policy</h1>",
        "workflow": ["review", "approve"],
    }
    resp = client.post("/document-types", json=data, headers=hdrs)
    assert resp.status_code == 201
    resp = client.get("/document-types", headers=hdrs)
    assert resp.status_code == 200
    names = {d["name"] for d in resp.json()}
    assert "policy" in names
    resp = client.get("/document-types/policy", headers=hdrs)
    assert resp.status_code == 200
    assert resp.json()["workflow"] == ["review", "approve"]

    updated = data | {"template": "<h1>Updated</h1>"}
    resp = client.put("/document-types/policy", json=updated, headers=hdrs)
    assert resp.status_code == 200
    assert resp.json()["template"] == "<h1>Updated</h1>"

    resp = client.delete("/document-types/policy", headers=hdrs)
    assert resp.status_code == 204
    resp = client.get("/document-types", headers=hdrs)
    names = {d["name"] for d in resp.json()}
    assert "Test Document Type" in names
    assert "policy" not in names


def test_idempotent_add() -> None:
    """Adding the same document type twice should be a no-op."""
    doc = DocumentTypeModel(name="Duplicate", template="<h1>Dup</h1>", workflow=["Phase"])
    first = add_document_type(doc)
    second = add_document_type(doc)
    assert first == second


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
    with pytest.raises((ValueError, IsADirectoryError, PermissionError, OSError)):
        export_document_types(str(dest_dir))


def test_import_document_types_json_error() -> None:
    with pytest.raises(ValueError):
        import_document_types_json("{}")


def test_list_all_phases() -> None:
    phases = list_all_phases()
    assert isinstance(phases, list)


def test_document_type_import_export_endpoints() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()

    data = {"name": "policy", "template": "<h1>Policy</h1>", "workflow": ["Phase"]}
    resp = client.post("/document-types", json=data, headers=hdrs)
    assert resp.status_code == 201

    export_resp = client.get("/document-types/export", headers=hdrs)
    assert export_resp.status_code == 200
    payload = export_resp.text

    resp = client.delete("/document-types/policy", headers=hdrs)
    assert resp.status_code == 204

    import_resp = client.post(
        "/document-types/import",
        files={"file": ("types.json", payload, "application/json")},
        headers=hdrs,
    )
    assert import_resp.status_code == 201

    names = {d["name"] for d in import_resp.json()}
    assert "policy" in names
