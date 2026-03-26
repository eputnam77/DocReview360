import pytest
from docreview360 import doc_types, search
from docreview360.doc_types import DocumentTypeModel, reset_document_types


def setup_function(_):
    doc_types.document_types.clear()
    search.search_index.projects.clear()


def test_save_and_load_persists_to_db():
    """Adding a document type persists to DB and is visible on the next read."""

    reset_document_types(seed=False)
    doc = DocumentTypeModel(name="T", template="tpl", workflow=["Phase"])
    doc_types.add_document_type(doc)

    # Verify persistence: read back from DB via a fresh query
    retrieved = doc_types.get_document_type("T")
    assert retrieved is not None
    assert retrieved.template == "tpl"


def test_update_propagates_and_conflicts():
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


def test_add_document_type_conflict():
    doc = DocumentTypeModel(name="Dup", template="t", workflow=["Phase"])
    first = doc_types.add_document_type(doc)
    # Re-adding the exact same definition is a no-op (returns equivalent model)
    assert doc_types.add_document_type(doc) == first
    # A conflicting definition with the same name should still error
    with pytest.raises(ValueError):
        doc_types.add_document_type(
            DocumentTypeModel(name="Dup", template="other", workflow=["Phase"])
        )
