from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


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


def test_workflow_lifecycle() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.post(
        "/workflows",
        json={"project": "p1", "phases": ["draft", "review", "done"]},
        headers=hdrs,
    )
    assert resp.status_code == 201
    wf = resp.json()
    wf_id = wf["id"]
    assert wf["phase"] == "draft"

    resp = client.post(f"/workflows/{wf_id}/assign", json={"user": "alice"})
    assert resp.status_code == 200
    assert resp.json()["reviewers"] == ["alice"]

    resp = client.post(f"/workflows/{wf_id}/advance")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "review"
