from docuflow.monitoring import open_dashboard
from hypothesis import given
from hypothesis import strategies as st


@given(st.none())
def test_task71_property(_) -> None:
    assert open_dashboard().startswith("http")
