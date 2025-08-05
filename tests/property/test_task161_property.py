from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task161 import render_start_page


@given(st.text())
def test_task161_property(workflow_id: str) -> None:
    render_start_page(workflow_id)
