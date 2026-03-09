from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.search import ProjectModel, add_project


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


def test_dashboard_widgets_endpoint() -> None:
    add_project(ProjectModel(id="p1", name="Test"))
    client = TestClient(app)
    resp = client.get("/dashboard/widgets", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "assigned" in data
    assert "pending_approvals" in data
    assert "avg_quality_score" in data
    assert "routing_latency" in data
    assert isinstance(data["critic_models"], dict)
