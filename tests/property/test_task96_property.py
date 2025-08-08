from docreview360.stubs.task96 import format_plugin_guide
from hypothesis import given
from hypothesis import strategies as st


@given(st.text())
def test_task96_property(name: str) -> None:
    guide = format_plugin_guide(name)
    assert guide.startswith("# Plugin ")
