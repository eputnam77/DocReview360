from typing import Any

from docreview360.stubs.task94 import task94
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task94_property(_: Any) -> None:
    task94()
