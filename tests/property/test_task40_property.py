from docuflow.stubs.task40 import task40
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task40_property(_):
    assert task40() is None
