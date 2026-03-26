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


def test_archival_workflow() -> None:
    client = TestClient(app)
    headers = _alice_headers()
    # import a document
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "Archive me", "text/markdown")},
        headers=headers,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.post(f"/archive/{doc_id}", json={"metadata": {"note": "v1"}}, headers=headers)
    assert resp.status_code == 201
    record = resp.json()
    arch_id = record["id"]
    assert record["document_id"] == doc_id
    assert record["metadata"]["note"] == "v1"
    assert all(key in record for key in ["markdown", "html", "docx", "pdf"])

    resp = client.get(f"/archive/{arch_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == arch_id

    resp = client.get("/archive", headers=headers)
    ids = [r["id"] for r in resp.json()]
    assert arch_id in ids
