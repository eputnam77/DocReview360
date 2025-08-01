from typing import Any

from docreview360.stubs.task131 import task131
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task131_property(_: Any) -> None:
    assert isinstance(task131(), float)
