from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task57 import task57


@given(st.none())
def test_task57_property(_):
    assert task57() is None
