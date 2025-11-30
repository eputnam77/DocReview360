import pytest

from docreview360.doc_types import (
    DocumentTypeModel,
    add_document_type,
    delete_document_type,
    document_types,
    export_document_types,
    import_document_types,
    list_document_types,
)


def test_document_type_import_export(tmp_path) -> None:
    doc = DocumentTypeModel(name="policy", template="<h1>Policy</h1>", workflow=["Phase"])
    add_document_type(doc)
    export_file = tmp_path / "types.json"
    export_document_types(export_file)

    # clear and reload
    document_types.clear()
    import_document_types(export_file)

    names = {d.name for d in list_document_types()}
    assert "policy" in names

    # cleanup
    delete_document_type("policy")


def test_import_invalid_json(tmp_path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json")
    with pytest.raises(ValueError):
        import_document_types(bad_file)


def test_import_missing_file(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(RuntimeError):
        import_document_types(missing)
