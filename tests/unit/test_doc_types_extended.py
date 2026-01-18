import pytest

from docreview360 import doc_types
from docreview360.doc_types import DocumentTypeModel


def setup_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "doc_types.json")
    doc_types.document_types.clear()
    return tmp_path


def test_export_import_roundtrip(monkeypatch, tmp_path):
    setup_tmp(monkeypatch, tmp_path)
    doc_types.add_document_type(DocumentTypeModel(name="X", template="T", workflow=["A"]))
    dest = tmp_path / "export.json"
    doc_types.export_document_types(dest)
    doc_types.document_types.clear()
    doc_types.import_document_types(dest)
    assert "X" in doc_types.document_types


def test_export_path_validation(monkeypatch, tmp_path):
    setup_tmp(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        doc_types.export_document_types(tmp_path)


def test_import_invalid_json(monkeypatch, tmp_path):
    setup_tmp(monkeypatch, tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(ValueError):
        doc_types.import_document_types(bad)
