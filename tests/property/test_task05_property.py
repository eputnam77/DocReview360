from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task05 import task05


@given(st.none())
def test_task05_property(_):
    assert task05() is None
