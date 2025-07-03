from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task27 import task27


@given(st.none())
def test_task27_property(_):
    assert task27() is None
