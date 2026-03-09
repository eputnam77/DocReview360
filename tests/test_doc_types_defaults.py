from docreview360.doc_types import DEFAULT_DOC_TYPE_NAMES, list_document_types


def test_default_document_types() -> None:
    """Verify default document type names are defined."""
    assert len(DEFAULT_DOC_TYPE_NAMES) > 0
    # Verify all default names are non-empty strings
    assert all(isinstance(name, str) and name for name in DEFAULT_DOC_TYPE_NAMES)
