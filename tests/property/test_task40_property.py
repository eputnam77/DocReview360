from typing import Any

from docreview360.stubs.task40 import task40
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task40_property(_: Any) -> None:
    task40()
