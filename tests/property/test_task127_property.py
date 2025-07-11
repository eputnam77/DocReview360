from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task127 import task127


@given(st.none())
def test_task127_property(_):
    assert task127() is None
