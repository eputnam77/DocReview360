from hypothesis import given
from hypothesis import strategies as st

from docuflow.doc_types import document_types


@given(st.none())
def test_task65_property(_) -> None:
    assert "sample" in document_types
