from typing import Any

from docreview360.stubs.task180 import task180
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task180_property(_: Any) -> None:
    task180()
