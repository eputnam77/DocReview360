from typing import Any

from docreview360.stubs.task160 import task160
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task160_property(_: Any) -> None:
    task160()
