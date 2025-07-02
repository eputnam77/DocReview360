from fastapi.testclient import TestClient

from docuflow.api import app


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
    assert resp.json()[0]["name"] == "policy"
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
    assert resp.json() == []
