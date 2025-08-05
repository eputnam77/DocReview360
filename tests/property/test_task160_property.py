from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task160 import task160


@given(st.none())
def test_task160_property(_: Any) -> None:
    task160()
