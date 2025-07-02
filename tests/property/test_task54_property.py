from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task54 import task54


@given(st.none())
def test_task54_property(_):
    assert task54() is None
