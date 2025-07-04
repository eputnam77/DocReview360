from docuflow.stubs.task63 import task63
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task63_property(_):
    assert task63() is None
