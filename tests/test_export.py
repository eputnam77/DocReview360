from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.documents import DocumentModel


def test_export_markdown_and_html() -> None:
    client = TestClient(app)
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "Hello *world*", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "markdown"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert resp.text == "Hello *world*"

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "html"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "<pre>" in resp.text


def test_export_json_roundtrip() -> None:
    client = TestClient(app)
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "Hello *world*", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get(f"/documents/{doc_id}/export", params={"fmt": "json"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    model = DocumentModel.model_validate_json(resp.text)
    assert model.id == doc_id
    assert model.content == "Hello *world*"
