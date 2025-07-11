from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task05 import task05


@given(st.none())
def test_task05_property(_):
    assert task05() is None
