from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.logs import clear_logs


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


def test_logging_records_actions() -> None:
    clear_logs()
    client = TestClient(app)
    headers = _alice_headers()

    # create project logs event
    resp = client.post("/projects", json={"id": "l1", "name": "Log", "user": "alice"}, headers=headers)
    assert resp.status_code == 201

    # import document logs event
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
        data={"project": "l1", "user": "alice"},
        headers=headers,
    )
    assert resp.status_code == 201

    headers = {**headers, "X-User": "alice"}
    resp = client.get("/logs", headers=headers)
    events = resp.json()
    actions = {e["action"] for e in events}
    assert "create_project" in actions
    assert "import_document" in actions

    first_id = events[0]["id"]
    resp = client.get("/logs", params={"log_id": first_id}, headers=headers)
    found = resp.json()
    assert len(found) == 1 and found[0]["id"] == first_id

    resp = client.get("/logs", params={"action": "import_document"}, headers=headers)
    filtered = resp.json()
    assert len(filtered) == 1
    assert filtered[0]["details"]["filename"] == "doc.md"

    resp = client.get("/logs", params={"severity": "info", "limit": 1}, headers=headers)
    assert len(resp.json()) == 1
