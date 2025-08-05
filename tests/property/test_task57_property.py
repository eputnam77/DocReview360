from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task57 import task57


@given(st.none())
def test_task57_property(_: Any) -> None:
    task57()
