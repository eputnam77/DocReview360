from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task168 import task168


@given(st.none())
def test_task168_property(_):
    assert task168() is None
