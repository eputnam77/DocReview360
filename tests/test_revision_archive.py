from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from docreview360.archive import archives
from fastapi.testclient import TestClient


def _auth_headers() -> dict[str, str]:
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


def test_promote_revision_archives_document() -> None:
    client = TestClient(app)
    hdrs = _auth_headers()
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "initial", "text/markdown")},
        headers=hdrs,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.post(
        f"/documents/{doc_id}/revisions",
        json={"content": "final", "promote": True},
        headers=hdrs,
    )
    assert resp.status_code == 201
    data = resp.json()
    arch_id = data.get("archiveId")
    assert arch_id is not None
    assert arch_id in archives
    assert archives[arch_id].document_id == doc_id
