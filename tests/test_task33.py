from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from docreview360.reporting import summary_csv
from fastapi.testclient import TestClient


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice", auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_summary_csv_helper() -> None:
    csv = summary_csv()
    assert csv.startswith("projects")
    header = csv.splitlines()[0]
    assert "avg_quality_score" in header


def test_summary_csv_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/reports/summary.csv", headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.text.startswith("projects")
