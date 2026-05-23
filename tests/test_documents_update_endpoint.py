from datetime import timedelta

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.documents import import_document


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


def test_update_document_accepts_editor_content_patch() -> None:
    client = TestClient(app)
    headers = _alice_headers()
    doc = import_document("editor-patch.md", b"original", user="alice")

    response = client.put(
        f"/documents/{doc.id}",
        json={"content": "updated from frontend editor"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == doc.id
    assert body["content"] == "updated from frontend editor"
    assert body["version_number"] == doc.version_number
