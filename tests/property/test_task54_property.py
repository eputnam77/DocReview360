from typing import Any

from docreview360.stubs.task54 import task54
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task54_property(_: Any) -> None:
    task54()
