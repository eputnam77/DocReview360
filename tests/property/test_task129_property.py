from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task129 import task129


@given(st.none())
def test_task129_property(_: Any) -> None:
    task129()
