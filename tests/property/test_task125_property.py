from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task125 import task125


@given(st.none())
def test_task125_property(_: Any) -> None:
    task125()
