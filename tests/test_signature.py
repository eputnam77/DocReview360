from docreview360.api import app
from fastapi.testclient import TestClient


def test_signature_flow() -> None:
    client = TestClient(app)
    # import a document
    resp = client.post("/documents/import", files={"file": ("doc.md", b"hello", "text/markdown")})
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    resp = client.post(
        f"/sign/{doc_id}",
        data={"user": "alice"},
    )
    assert resp.status_code == 200
    sig_id = resp.json()["id"]
    assert "url" in resp.json()
    status = client.get(f"/sign/{sig_id}").json()["status"]
    assert status == "pending"
    client.post("/hooks/documenso", json={"id": sig_id, "status": "signed"})
    status2 = client.get(f"/sign/{sig_id}").json()["status"]
    assert status2 == "signed"
