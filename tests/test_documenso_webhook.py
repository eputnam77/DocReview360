import hashlib
import hmac
import json
import os
from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient


def _auth_headers() -> dict[str, str]:
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


def test_documenso_webhook_advances_workflow() -> None:
    client = TestClient(app)
    hdrs = _auth_headers()
    # create workflow with signed phase
    resp = client.post(
        "/workflows", json={"project": "p1", "phases": ["draft", "signed"]}, headers=hdrs
    )
    wf_id = resp.json()["id"]

    # import document
    resp = client.post("/documents/import", files={"file": ("d.md", b"data", "text/markdown")}, headers=hdrs)
    doc_id = resp.json()["id"]

    # request signature linked to workflow
    resp = client.post(f"/sign/{doc_id}", data={"user": "bob", "workflow": wf_id}, headers=hdrs)
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
    assert client.get(f"/sign/{sig_id}", headers=hdrs).json()["status"] == "signed"
    wf_data = client.get(f"/workflows/{wf_id}", headers=hdrs).json()
    assert wf_data["phase"] == "signed"
