from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient


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


def test_sign_approval_flow() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    wf = client.post(
        "/workflows",
        json={"project": "p42", "phases": ["draft", "signed"]},
        headers=hdrs,
    ).json()
    appr = client.post(
        "/approvals",
        json={"workflow": wf["id"], "reviewer": "jane"},
        headers=hdrs,
    ).json()

    resp = client.post(f"/approvals/{appr['id']}/sign", headers=hdrs)
    assert resp.status_code == 200
    sig_id = resp.json()["id"]

    client.post(f"/sign/{sig_id}/complete", headers=hdrs)

    appr2 = client.get(f"/approvals/{appr['id']}", headers=hdrs).json()
    assert appr2["state"] == "approved"
    assert appr2["signature"] == sig_id


def test_sign_approval_duplicate_returns_conflict() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    wf = client.post(
        "/workflows",
        json={"project": "p43", "phases": ["draft", "signed"]},
        headers=hdrs,
    ).json()
    appr = client.post(
        "/approvals",
        json={"workflow": wf["id"], "reviewer": "jane"},
        headers=hdrs,
    ).json()

    resp1 = client.post(f"/approvals/{appr['id']}/sign", headers=hdrs)
    assert resp1.status_code == 200
    sig_id = resp1.json()["id"]

    client.post(f"/sign/{sig_id}/complete", headers=hdrs)

    resp2 = client.post(f"/approvals/{appr['id']}/sign", headers=hdrs)
    assert resp2.status_code == 409
