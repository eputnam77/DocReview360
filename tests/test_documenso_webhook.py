import hashlib
import hmac
import json
import os

from fastapi.testclient import TestClient

from docreview360.api import app


def test_documenso_webhook_advances_workflow() -> None:
    client = TestClient(app)
    # create workflow with signed phase
    resp = client.post("/workflows", json={"project": "p1", "phases": ["draft", "signed"]})
    wf_id = resp.json()["id"]

    # import document
    resp = client.post("/documents/import", files={"file": ("d.md", b"data", "text/markdown")})
    doc_id = resp.json()["id"]

    # request signature linked to workflow
    resp = client.post(f"/sign/{doc_id}", data={"user": "bob", "workflow": wf_id})
    sig_id = resp.json()["id"]

    # webhook callback marks signed
    secret = "testsecret"
    os.environ["DOCUMENSO_WEBHOOK"] = secret
    payload = {"id": sig_id, "status": "signed"}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    client.post(
        "/hooks",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Provider": "documenso",
            "X-Signature": signature,
        },
    )

    # status updated and workflow advanced
    assert client.get(f"/sign/{sig_id}").json()["status"] == "signed"
    wf_data = client.get(f"/workflows/{wf_id}").json()
    assert wf_data["phase"] == "signed"
