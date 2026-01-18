from docreview360 import doc_types
from docreview360.doc_types import DEFAULT_DOC_TYPE_NAMES, _bootstrap_sample


def test_default_document_types() -> None:
    doc_types.document_types.clear()
    _bootstrap_sample()
    assert set(doc_types.document_types.keys()) == set(DEFAULT_DOC_TYPE_NAMES)
