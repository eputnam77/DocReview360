from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task97 import enable_observability


@given(st.text())
def test_task97_property(service: str) -> None:
    config = enable_observability(service)
    assert config["service"] == service
