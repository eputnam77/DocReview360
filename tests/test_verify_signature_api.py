from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.approvals import create_approval, send_for_signature
from docreview360.integrations.signature import documenso


def test_verify_signature_endpoint() -> None:
    client = TestClient(app)
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", b"hello", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    appr = create_approval("wf1", "alice", document=b"hello")
    send_for_signature(appr.id, doc_id, "alice")
    documenso.process_webhook(
        {
            "id": appr.signature_id,
            "status": "signed",
            "certificate_url": "cert",
        }
    )

    resp2 = client.get(f"/documents/{doc_id}/verify-signature")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "pass"
    assert data["details"][0]["approval_id"] == appr.id
