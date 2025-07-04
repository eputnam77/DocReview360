from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task52 import task52


@given(st.none())
def test_task52_property(_):
    assert task52() is None
