from typing import Any

from docreview360.stubs.task166 import task166
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task166_property(_: Any) -> None:
    task166()
