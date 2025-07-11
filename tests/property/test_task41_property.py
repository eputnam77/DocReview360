from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task41 import task41


@given(st.none())
def test_task41_property(_):
    assert task41() == ["one", "two"]
