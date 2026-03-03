import hashlib
import hmac
import json
import os
from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for a test 'alice' admin user."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass  # user may already exist
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_signature_flow() -> None:
    client = TestClient(app)
    headers = _alice_headers()
    # import a document
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", b"hello", "text/markdown")},
        headers=headers,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    resp = client.post(
        f"/sign/{doc_id}",
        data={"user": "alice"},
        headers=headers,
    )
    assert resp.status_code == 200
    sig_id = resp.json()["id"]
    assert "url" in resp.json()
    status = client.get(f"/sign/{sig_id}").json()["status"]
    assert status == "pending"
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
    status2 = client.get(f"/sign/{sig_id}").json()["status"]
    assert status2 == "signed"
