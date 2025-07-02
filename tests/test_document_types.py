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
