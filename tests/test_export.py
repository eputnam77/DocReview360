from datetime import timedelta

from docreview360 import auth
from docreview360.api import app
from docreview360.documents import DocumentModel
from docreview360.exporter import export_document
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


def test_export_markdown_and_html() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "Hello *world*", "text/markdown")},
        headers=hdrs,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "markdown"}, headers=hdrs)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert resp.text == "Hello *world*"

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "html"}, headers=hdrs)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "<pre>" in resp.text


def test_export_txt_and_xml() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "Hello *world*", "text/markdown")},
        headers=hdrs,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "txt"}, headers=hdrs)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text == "Hello *world*"

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "xml"}, headers=hdrs)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert "<document" in resp.text
    assert "<content>" in resp.text


def test_export_json_roundtrip() -> None:
    client = TestClient(app)
    hdrs = _alice_headers()
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "Hello *world*", "text/markdown")},
        headers=hdrs,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "json"}, headers=hdrs)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    model = DocumentModel.model_validate_json(resp.text)
    assert model.id == doc_id
    assert model.content == "Hello *world*"


def test_export_pdf_format() -> None:
    doc = DocumentModel(id="1", content="Hello")
    data, media, name = export_document(doc, "pdf")
    assert media == "application/pdf"
    assert name.endswith(".pdf")
    assert data.startswith(b"%PDF")
