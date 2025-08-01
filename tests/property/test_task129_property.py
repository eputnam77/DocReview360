from typing import Any

from docreview360.stubs.task129 import task129
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task129_property(_: Any) -> None:
    task129()
