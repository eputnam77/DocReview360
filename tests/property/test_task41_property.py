from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task41 import task41


@given(st.none())
def test_task41_property(_):
    assert task41() is None
