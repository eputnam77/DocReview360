from typing import Any

from docreview360.stubs.task130 import task130
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task130_property(_: Any) -> None:
    task130()
