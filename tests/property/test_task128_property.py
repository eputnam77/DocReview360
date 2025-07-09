from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task128 import task128


@given(st.none())
def test_task128_property(_):
    assert task128() is None
