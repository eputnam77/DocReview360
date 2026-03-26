from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from docreview360.archive import archive_document, archives
from docreview360.documents import DocumentModel, documents
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


def test_archive_stores_report_and_endpoint(tmp_path):
    archives.clear()
    doc = DocumentModel(id="d1", content="sample")
    documents["d1"] = doc  # register doc so endpoint can find it
    record = archive_document(doc, bucket=tmp_path, check_results={"grammar": ["ok"]})
    assert record.report_html and record.report_pdf
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.get(f"/archive/{record.id}/report/html", headers=hdrs)
    assert resp.status_code == 200
    assert "Check Results" in resp.text
    resp = client.get(f"/archive/{record.id}/report/pdf", headers=hdrs)
    assert resp.status_code == 200
    assert resp.content.startswith(b"PDF-PLACEHOLDER")
