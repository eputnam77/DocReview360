from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task94 import task94


@given(st.none())
def test_task94_property(_):
    assert task94() is None
