from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task182 import task182


@given(st.none())
def test_task182_property(_):
    assert task182() is None
