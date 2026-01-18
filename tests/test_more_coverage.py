from pathlib import Path

import pytest

import docreview360.ai_utils as ai
from docreview360.doc_types import (
    DocumentTypeModel,
    export_document_types,
    update_document_type,
)


def test_update_nonexistent_type_raises() -> None:
    with pytest.raises(KeyError):
        update_document_type(
            "missing",
            DocumentTypeModel(name="x", template="t", workflow=["Phase"]),
        )


def test_export_to_directory_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        export_document_types(tmp_path)


def test_ai_utils_suggest_and_validate() -> None:
    assert ai.suggest_document_type("Annual Report") == "report"
    assert ai.suggest_document_type("Service Invoice") == "invoice"
    assert ai.suggest_document_type("Other") == "sample"

    assert ai.validate_content("Valid text") is True
    assert ai.validate_content("URGENT bad") is False
    assert ai.validate_content("   ") is False
