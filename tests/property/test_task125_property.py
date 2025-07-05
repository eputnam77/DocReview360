from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task125 import task125


@given(st.none())
def test_task125_property(_):
    assert task125() is None
