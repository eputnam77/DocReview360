from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task126 import task126


@given(st.text(), st.text())
def test_task126_property(url: str, token: str) -> None:
    task126(url, token)
