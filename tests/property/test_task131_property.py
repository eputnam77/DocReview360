from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task131 import task131


@given(st.none())
def test_task131_property(_):
    assert isinstance(task131(), float)
