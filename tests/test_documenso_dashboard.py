import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.integrations.signature import documenso


def _auth_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_updates_after_signature() -> None:
    client = TestClient(app)
    hdrs = _auth_headers()
    client.post("/projects", json={"id": "d1", "name": "Doc"}, headers=hdrs)
    wf = client.post("/workflows", json={"project": "d1", "phases": ["draft", "signed"]}).json()
    doc = client.post(
        "/documents/import",
        files={"file": ("f.txt", b"hi", "text/plain")},
        data={"project": "d1"},
        headers=hdrs,
    ).json()
    appr = client.post(
        "/approvals",
        json={"workflow": wf["id"], "reviewer": "bob", "doc_id": doc["id"]},
    ).json()
    sig = client.post(f"/approvals/{appr['id']}/sign").json()["id"]

    entry = next(e for e in client.get("/reports/dashboard").json() if e["id"] == "d1")
    pending = entry["pending_approvals"]
    assert pending >= 1

    secret = "testsecret"
    os.environ["DOCUMENSO_WEBHOOK"] = secret
    cert_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Test")])
    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(cert_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(cert_key, hashes.SHA256())
    )
    content = b"hi"
    cert_sig = cert_key.sign(content, padding.PKCS1v15(), hashes.SHA256())
    cert_url = "https://dashboard-cert"
    documenso.register_test_certificate(cert_url, cert, cert_sig)

    payload = {"id": sig, "status": "signed", "certificate_url": cert_url}
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
    entry2 = next(e for e in client.get("/reports/dashboard").json() if e["id"] == "d1")
    assert entry2["pending_approvals"] == pending - 1
