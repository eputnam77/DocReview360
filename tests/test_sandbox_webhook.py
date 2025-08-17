import hashlib
import hmac
import json
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.monitoring import HASH_MISMATCHES


def test_sandbox_webhook_idempotent(monkeypatch):
    monkeypatch.setenv("SIGNATURE_PROVIDER", "sandbox")
    secret = "sandboxsecret"
    monkeypatch.setenv("SANDBOX_WEBHOOK", secret)
    client = TestClient(app)

    resp = client.post("/documents/import", files={"file": ("d.md", b"data", "text/markdown")})
    doc_id = resp.json()["id"]
    resp = client.post(f"/sign/{doc_id}", data={"user": "bob"})
    sig_id = resp.json()["id"]

    payload = {
        "id": sig_id,
        "status": "signed",
        "signed_at": (datetime.utcnow() - timedelta(seconds=1)).isoformat(),
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    for _ in range(2):
        res = client.post(
            "/hooks",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Provider": "sandbox",
                "X-Signature": signature,
            },
        )
        assert res.status_code == 204

    status = client.get(f"/sign/{sig_id}").json()["status"]
    assert status == "signed"


def test_webhook_hash_mismatch(monkeypatch):
    monkeypatch.setenv("SIGNATURE_PROVIDER", "sandbox")
    monkeypatch.setenv("SANDBOX_WEBHOOK", "secret")
    client = TestClient(app)

    payload = {"id": "1", "status": "signed"}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()

    before = HASH_MISMATCHES.labels("sandbox")._value.get()
    res = client.post(
        "/hooks",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Provider": "sandbox",
            "X-Signature": "bad",
        },
    )
    assert res.status_code == 400
    after = HASH_MISMATCHES.labels("sandbox")._value.get()
    assert after == before + 1
