from docuflow.stubs.task57 import task57
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task57_property(_):
    assert task57() is None
