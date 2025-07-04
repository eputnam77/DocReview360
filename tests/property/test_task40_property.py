from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task40 import task40


@given(st.none())
def test_task40_property(_):
    assert task40() is None
