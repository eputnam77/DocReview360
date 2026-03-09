from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.doc_types import reset_document_types


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


def test_document_type_crud_via_api() -> None:
    reset_document_types(seed=False)
    client = TestClient(app)
    hdrs = _alice_headers()

    payload = {"name": "APIType", "template": "", "workflow": []}
    r = client.post("/document-types", json=payload, headers=hdrs)
    assert r.status_code == 201

    assert any(d["name"] == "APIType" for d in client.get("/document-types", headers=hdrs).json())
    assert client.get("/document-types/APIType", headers=hdrs).json()["name"] == "APIType"

    update = {"name": "APITypeRenamed", "template": "", "workflow": []}
    r = client.put("/document-types/APIType", json=update, headers=hdrs)
    assert r.json()["name"] == "APITypeRenamed"

    usage = client.get("/document-types/APITypeRenamed/usage", headers=hdrs).json()
    assert usage["usage_count"] == 0

    # Export and re-import document types via API
    export = client.get("/document-types/export", headers=hdrs)
    assert export.status_code == 200
    r = client.post(
        "/document-types/import",
        files={"file": ("types.json", export.content, "application/json")},
        headers=hdrs,
    )
    assert any(d["name"] == "APITypeRenamed" for d in r.json())

    r = client.delete("/document-types/APITypeRenamed", headers=hdrs)
    assert r.status_code == 204

    reset_document_types(seed=False)
