from typing import Any

from docreview360.stubs.task182 import task182
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task182_property(_: Any) -> None:
    task182()
