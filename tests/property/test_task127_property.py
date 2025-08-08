from typing import Any

from docreview360.stubs.task127 import task127
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task127_property(_: Any) -> None:
    task127()
