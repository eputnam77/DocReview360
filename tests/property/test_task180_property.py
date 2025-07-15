from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task180 import task180


@given(st.none())
def test_task180_property(_: Any) -> None:
    task180()
