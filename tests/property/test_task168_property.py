from typing import Any

from docreview360.stubs.task168 import task168
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task168_property(_: Any) -> None:
    task168()
