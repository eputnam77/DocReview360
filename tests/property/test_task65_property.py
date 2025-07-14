from hypothesis import given
from hypothesis import strategies as st

from docreview360.doc_types import document_types


@given(st.none())
def test_task65_property(_unused: object) -> None:
    assert "sample" in document_types
