from docreview360.doc_types import (
    DEFAULT_DOC_TYPE_NAMES,
    _bootstrap_sample,
    document_types,
)


def test_default_document_types() -> None:
    document_types.clear()
    _bootstrap_sample()
    assert set(document_types.keys()) == set(DEFAULT_DOC_TYPE_NAMES)
