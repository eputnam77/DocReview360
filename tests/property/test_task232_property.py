from typing import Any

from docreview360.stubs.task232 import task232
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task232_property(_: Any) -> None:
    task232()
