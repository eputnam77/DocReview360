from datetime import timedelta

from docreview360 import auth, project_preferences
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


def test_project_preferences_persist(tmp_path, monkeypatch) -> None:
    path = tmp_path / "settings.yaml"
    monkeypatch.setattr(project_preferences, "SETTINGS_FILE", path)
    hdrs = _alice_headers()

    client = TestClient(app)
    project_id = "demo-project"
    resp = client.put(
        f"/projects/{project_id}/preferences",
        json={"lint": True, "collab": True, "watermark_text": "Secret"},
        headers=hdrs,
    )
    assert resp.status_code == 200
    assert resp.json()["lint"] is True

    client2 = TestClient(app)
    resp2 = client2.get(f"/projects/{project_id}/preferences", headers=hdrs)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["lint"] is True
    assert data["collab"] is True
    assert data["watermark_text"] == "Secret"
