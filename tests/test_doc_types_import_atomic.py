from __future__ import annotations

import json

import pytest
from docreview360 import doc_types
from docreview360.doc_types import DocumentTypeModel, import_document_types_json


def test_import_document_types_json_atomic(tmp_path, monkeypatch) -> None:
    """A bad entry should not wipe existing document types."""

    # Isolate persistence to a temporary file to avoid touching the repo
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "doc_types.json")

    doc_types.document_types.clear()
    original = {"Existing": DocumentTypeModel(name="Existing", template="", workflow=["Draft"])}
    doc_types.document_types.update(original)

    bad_payload = json.dumps(
        [
            {"name": "Valid", "template": "", "workflow": ["Draft"]},
            {"invalid": "entry"},
        ]
    )

    with pytest.raises(ValueError):
        import_document_types_json(bad_payload)

    # Ensure the original data remains intact
    assert doc_types.document_types == original
