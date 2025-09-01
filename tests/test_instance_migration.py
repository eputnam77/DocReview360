from docreview360.migration import export_instance, import_instance
from docreview360.doc_types import document_types


def test_export_import_roundtrip(tmp_path):
    path = tmp_path / "instance.gz"
    export_instance(path)
    assert path.exists()
    # mutate state then restore
    document_types.clear()
    import_instance(path)
    assert document_types  # restored from export
