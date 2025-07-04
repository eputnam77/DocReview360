from docuflow.api import app
from fastapi.testclient import TestClient


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
    assert names == {"sample"}


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
