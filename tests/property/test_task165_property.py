from typing import Any

from docreview360.stubs.task165 import task165
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task165_property(_: Any) -> None:
    task165()
