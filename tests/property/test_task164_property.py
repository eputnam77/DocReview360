from docreview360.stubs.task164 import analyze_performance
from hypothesis import given
from hypothesis import strategies as st


@given(st.integers(min_value=1, max_value=10))
def test_task164_property(iterations: int) -> None:
    analyze_performance(iterations)
