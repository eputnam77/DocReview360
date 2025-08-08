from typing import Any

from docreview360.stubs.task128 import task128
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task128_property(_: Any) -> None:
    task128()
