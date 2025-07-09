from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task130 import task130


@given(st.none())
def test_task130_property(_):
    assert task130() is None
