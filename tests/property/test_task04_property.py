from typing import Any

from docreview360.stubs.task04 import task04
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task04_property(_: Any) -> None:
    task04()
