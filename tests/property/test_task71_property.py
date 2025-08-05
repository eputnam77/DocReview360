from hypothesis import given
from hypothesis import strategies as st

from docreview360.monitoring import open_dashboard


@given(st.none())
def test_task71_property(_unused: object) -> None:
    assert open_dashboard().startswith("http")
