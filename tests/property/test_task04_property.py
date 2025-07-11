from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task04 import task04


@given(st.none())
def test_task04_property(_):
    assert task04() is None
