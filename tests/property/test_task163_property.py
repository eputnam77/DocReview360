from hypothesis import given
from hypothesis import strategies as st

from docreview360.stubs.task163 import render_extension_menu


@given(st.lists(st.text()))
def test_task163_property(enabled: list[str]) -> None:
    render_extension_menu(enabled)
