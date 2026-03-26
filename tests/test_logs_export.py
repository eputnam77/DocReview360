from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from docreview360.logs import clear_logs
from fastapi.testclient import TestClient


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


def _setup_logs() -> None:
    clear_logs()
    client = TestClient(app)
    hdrs = _alice_headers()
    client.post("/projects", json={"id": "p1", "name": "Proj", "user": "alice"}, headers=hdrs)
    client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
        data={"project": "p1", "user": "alice"},
        headers=hdrs,
    )


def test_export_logs_json() -> None:
    _setup_logs()
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.get(
        "/logs/export",
        params={"fmt": "json", "action": "create_project"},
        headers=hdrs,
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["metadata"]["filters"]["action"] == "create_project"
    assert len(data["logs"]) == 1


def test_export_logs_csv() -> None:
    _setup_logs()
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.get(
        "/logs/export",
        params={"fmt": "csv", "action": "import_document"},
        headers=hdrs,
    )
    text = resp.text
    assert resp.status_code == 200
    assert text.startswith("# Generated at:")
    assert "# Filters: action=import_document" in text
    assert "import_document" in text.splitlines()[-1]


def test_export_logs_pdf() -> None:
    _setup_logs()
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.get("/logs/export", params={"fmt": "pdf"}, headers=hdrs)
    content = resp.content
    assert resp.status_code == 200
    assert content.startswith(b"%PDF-1.4")
    assert b"Generated at:" in content
