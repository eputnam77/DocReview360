from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task183 import task183


@given(st.none())
def test_task183_property(_):
    assert task183() is None
