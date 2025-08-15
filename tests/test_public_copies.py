from docreview360.api import app
from docreview360.archive import archive_document
from docreview360.documents import DocumentModel, documents
from fastapi.testclient import TestClient


def test_public_copy_listing_and_archive(tmp_path) -> None:
    backup = documents.copy()
    documents.clear()
    try:
        internal = DocumentModel(id="int1", content="internal")
        public = DocumentModel(
            id="pub1",
            content="public",
            public_copy=True,
            source_document_id="int1",
        )
        documents[internal.id] = internal
        documents[public.id] = public

        client = TestClient(app)
        resp = client.get("/documents/public")
        assert resp.status_code == 200
        data = resp.json()
        assert data == [
            {
                "id": "pub1",
                "content": "public",
                "history": [],
                "editor": "tiptap",
                "number": None,
                "project": None,
                "user": None,
                "date": None,
                "priority": None,
                "ingestion_hash": None,
                "public_copy": True,
                "source_document_id": "int1",
            }
        ]

        record = archive_document(public, bucket=tmp_path)
        assert record.metadata["public_copy"] is True
        assert record.metadata["source_doc_id"] == "int1"

        report = client.get("/documents/public/report")
        assert report.status_code == 200
        assert report.json() == [{"id": "pub1", "source_document_id": "int1"}]
    finally:
        documents.clear()
        documents.update(backup)
