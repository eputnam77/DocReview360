from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task90 import task90


@given(st.none())
def test_task90_property(_):
    assert task90() is None
