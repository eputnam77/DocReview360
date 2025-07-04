from docuflow.stubs.task87 import render_chart
from hypothesis import given
from hypothesis import strategies as st


@given(st.text(), st.dictionaries(st.text(), st.integers()))
def test_task87_property(name: str, values: dict[str, int]) -> None:
    yaml = render_chart(name, values)
    assert isinstance(yaml, str)
