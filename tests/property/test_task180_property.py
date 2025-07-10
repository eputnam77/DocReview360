from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task180 import task180


@given(st.none())
def test_task180_property(_):
    assert task180() is None
