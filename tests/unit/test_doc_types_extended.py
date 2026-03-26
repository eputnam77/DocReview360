"""Tests for document type export/import and validation (DB-backed)."""

import json

import pytest
from docreview360.doc_types import (
    DocumentTypeModel,
    add_document_type,
    export_document_types,
    import_document_types,
    list_document_types,
    reset_document_types,
)


@pytest.fixture(autouse=True)
def clean_doc_types():
    """Reset doc types before and after each test."""
    reset_document_types(seed=False)
    yield
    reset_document_types(seed=False)


def test_export_import_roundtrip(tmp_path):
    """Exported doc types can be re-imported successfully."""
    add_document_type(DocumentTypeModel(name="X", template="T", workflow=["A"]))
    dest = tmp_path / "export.json"
    export_document_types(str(dest))
    reset_document_types(seed=False)
    import_document_types(str(dest))
    names = [dt.name for dt in list_document_types()]
    assert "X" in names


def test_export_path_validation(tmp_path):
    """export_document_types raises ValueError when path is a directory."""
    with pytest.raises((ValueError, IsADirectoryError, PermissionError, OSError)):
        export_document_types(str(tmp_path))


def test_import_invalid_json(tmp_path):
    """import_document_types raises ValueError for malformed JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        import_document_types(str(bad))
