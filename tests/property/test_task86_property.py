from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task86 import task86


@given(st.none())
def test_task86_property(_):
    assert task86() is None
