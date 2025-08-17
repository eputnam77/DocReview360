from docreview360.documents import (
    get_document_version,
    get_document_versions,
    import_document,
    update_document,
)


def test_version_history_access() -> None:
    doc = import_document("doc.md", b"v1")
    update_document(doc.id, "v2")
    update_document(doc.id, "v3")
    versions = get_document_versions(doc.id)
    assert versions == ["v1", "v2", "v3"]
    assert get_document_version(doc.id, 0) == "v1"
    assert get_document_version(doc.id, 1) == "v2"
