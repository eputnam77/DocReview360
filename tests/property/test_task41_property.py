from typing import Any

from docreview360.stubs.task41 import task41
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task41_property(_: Any) -> None:
    assert task41() == ["one", "two"]
