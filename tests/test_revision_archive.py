from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.archive import archives


def test_promote_revision_archives_document() -> None:
    client = TestClient(app)
    resp = client.post(
        "/documents/import",
        files={"file": ("doc.md", "initial", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.post(
        f"/documents/{doc_id}/revisions",
        json={"content": "final", "promote": True},
    )
    assert resp.status_code == 201
    data = resp.json()
    arch_id = data.get("archiveId")
    assert arch_id is not None
    assert arch_id in archives
    assert archives[arch_id].document_id == doc_id
