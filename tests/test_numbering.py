from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
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


def test_project_document_numbering() -> None:
    client = TestClient(app)
    headers = _alice_headers()

    resp = client.post(
        "/projects",
        json={"id": "pnum", "name": "Numbered"},
        headers=headers,
    )
    assert resp.status_code == 201
    project = resp.json()
    assert isinstance(project["number"], int)

    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "content", "text/markdown")},
        data={"project": "pnum"},
        headers=headers,
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert isinstance(doc["number"], int)
