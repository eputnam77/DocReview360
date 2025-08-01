from docreview360.stubs.task52 import task52
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
@given(st.from_regex(r"[A-Za-z_][A-Za-z0-9_]*", fullmatch=True))
def test_task52_property(name: str) -> None:
    assert name in task52(name)
