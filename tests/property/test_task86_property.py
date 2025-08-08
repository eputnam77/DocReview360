from docreview360.stubs.task86 import has_trivy_step
from hypothesis import given
from hypothesis import strategies as st


@given(st.text())
def test_task86_property(text: str) -> None:
    """``has_trivy_step`` should always return a boolean."""
    assert isinstance(has_trivy_step(text), bool)
