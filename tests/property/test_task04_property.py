from docuflow.stubs.task04 import task04
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task04_property(_):
    assert task04() is None
