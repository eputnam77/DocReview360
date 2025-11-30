from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.archive import archive_document, archives
from docreview360.documents import DocumentModel


def test_archive_stores_report_and_endpoint(tmp_path):
    archives.clear()
    doc = DocumentModel(id="d1", content="sample")
    record = archive_document(doc, bucket=tmp_path, check_results={"grammar": ["ok"]})
    assert record.report_html and record.report_pdf
    client = TestClient(app)
    resp = client.get(f"/archive/{record.id}/report/html")
    assert resp.status_code == 200
    assert "Check Results" in resp.text
    resp = client.get(f"/archive/{record.id}/report/pdf")
    assert resp.status_code == 200
    assert resp.content.startswith(b"PDF-PLACEHOLDER")
