from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import docreview360.doc_types as doc_types_module


@pytest.fixture(autouse=True)
def _isolate_doc_types(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Prevent persistence side effects and reset in-memory state."""

    monkeypatch.setenv("DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", "0")
    monkeypatch.setattr(doc_types_module, "DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", False)
    monkeypatch.setattr(doc_types_module, "DATA_FILE", tmp_path / "doc_types.json")
    doc_types_module.document_types.clear()
    yield
    doc_types_module.document_types.clear()


def test_add_document_type_requires_workflow() -> None:
    """Adding a document type without workflow phases should fail validation."""

    with pytest.raises(ValidationError):
        doc_types_module.add_document_type({"name": "No Workflow", "template": "<h1>Invalid</h1>"})


def test_update_document_type_revalidates() -> None:
    """Updating with an invalid workflow should propagate the validation error."""

    valid = doc_types_module.DocumentTypeModel(
        name="Valid", template="<h1>Valid</h1>", workflow=["Draft"]
    )
    doc_types_module.add_document_type(valid)
    invalid = doc_types_module.DocumentTypeModel.model_construct(
        name="Valid", template="<h1>Valid</h1>", workflow=[]
    )
    with pytest.raises(ValidationError):
        doc_types_module.update_document_type("Valid", invalid)
