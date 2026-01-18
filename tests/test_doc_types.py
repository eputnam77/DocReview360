import pytest

from docreview360 import doc_types, search
from docreview360.doc_types import DocumentTypeModel, reset_document_types


def setup_function(_):
    doc_types.document_types.clear()
    search.search_index.projects.clear()


def test_save_and_load_state(tmp_path, monkeypatch):
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "types.json")
    monkeypatch.setattr(doc_types, "DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", True)
    reset_document_types()
    doc = DocumentTypeModel(name="T", template="tpl", workflow=["Phase"])
    doc_types.add_document_type(doc)
    doc_types.document_types.clear()
    assert doc_types.load_state() is True
    assert doc_types.document_types["T"].template == "tpl"


def test_update_propagates_and_conflicts(tmp_path, monkeypatch):
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "types.json")
    old = DocumentTypeModel(name="Old", template="t", workflow=["Phase"])
    existing = DocumentTypeModel(name="Existing", template="t", workflow=["Phase"])
    doc_types.add_document_type(old)
    doc_types.add_document_type(existing)
    project = search.ProjectModel(id="p1", name="P", doc_type="Old")
    search.search_index.add_project(project)
    updated = DocumentTypeModel(name="New", template="t", workflow=["Phase"])
    doc_types.update_document_type("Old", updated)
    assert search.projects["p1"].doc_type == "New"
    with pytest.raises(ValueError):
        doc_types.update_document_type(
            "New", DocumentTypeModel(name="Existing", template="t", workflow=["Phase"])
        )


def test_add_document_type_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "types.json")
    doc = DocumentTypeModel(name="Dup", template="t", workflow=["Phase"])
    first = doc_types.add_document_type(doc)
    # Re-adding the exact same definition is a no-op
    assert doc_types.add_document_type(doc) is first
    # A conflicting definition with the same name should still error
    with pytest.raises(ValueError):
        doc_types.add_document_type(
            DocumentTypeModel(name="Dup", template="other", workflow=["Phase"])
        )
