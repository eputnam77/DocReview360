from typing import Any

from docreview360.stubs.task57 import task57
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task57_property(_: Any) -> None:
    task57()
