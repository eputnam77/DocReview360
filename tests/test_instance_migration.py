import gzip
import json

import pytest
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


def test_import_instance_rejects_missing_sections(tmp_path) -> None:
    path = tmp_path / "broken.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"backup": "Zm9v"}, fh)

    with pytest.raises(ValueError, match="doc_types"):
        import_instance(path)


def test_import_instance_rejects_invalid_base64(tmp_path) -> None:
    path = tmp_path / "broken.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"backup": "!!!", "doc_types": []}, fh)

    with pytest.raises(ValueError, match="base64"):
        import_instance(path)
