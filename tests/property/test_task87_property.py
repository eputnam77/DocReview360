from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task87 import task87


@given(st.none())
def test_task87_property(_):
    assert task87() is None
