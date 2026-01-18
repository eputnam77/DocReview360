from docreview360 import doc_types
from docreview360.doc_types import DocumentTypeModel, add_document_type
from docreview360.migration import export_instance, import_instance


def test_export_import_roundtrip(tmp_path):
    add_document_type(DocumentTypeModel(name="Migration Seed", template="", workflow=["Phase"]))
    path = tmp_path / "instance.gz"
    export_instance(path)
    assert path.exists()
    # mutate state then restore
    doc_types.document_types.clear()
    import_instance(path)
    assert doc_types.document_types  # restored from export
