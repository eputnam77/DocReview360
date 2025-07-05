from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task52 import task52


@given(st.from_regex(r"[A-Za-z_][A-Za-z0-9_]*", fullmatch=True))
def test_task52_property(name: str) -> None:
    assert name in task52(name)
