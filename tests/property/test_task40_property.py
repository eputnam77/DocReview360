from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task40 import task40


@given(st.none())
def test_task40_property(_):
    assert task40() is None
