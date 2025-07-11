from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task130 import task130


@given(st.none())
def test_task130_property(_):
    assert task130() is None
