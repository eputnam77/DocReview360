from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task165 import task165


@given(st.none())
def test_task165_property(_: Any) -> None:
    task165()
