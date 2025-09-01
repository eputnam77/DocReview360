from __future__ import annotations

from fastapi.testclient import TestClient

from docreview360 import doc_types
from docreview360.api import app


def test_document_type_crud_via_api(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "doc_types.json")
    doc_types.document_types.clear()

    payload = {"name": "APIType", "template": "", "workflow": []}
    r = client.post("/document-types", json=payload)
    assert r.status_code == 201

    assert any(d["name"] == "APIType" for d in client.get("/document-types").json())
    assert client.get("/document-types/APIType").json()["name"] == "APIType"

    update = {"name": "APITypeRenamed", "template": "", "workflow": []}
    r = client.put("/document-types/APIType", json=update)
    assert r.json()["name"] == "APITypeRenamed"

    usage = client.get("/document-types/APITypeRenamed/usage").json()
    assert usage["usage_count"] == 0

    # Export and re-import document types via API
    export = client.get("/document-types/export")
    assert export.status_code == 200
    r = client.post(
        "/document-types/import",
        files={"file": ("types.json", export.content, "application/json")},
    )
    assert any(d["name"] == "APITypeRenamed" for d in r.json())

    r = client.delete("/document-types/APITypeRenamed")
    assert r.status_code == 204
