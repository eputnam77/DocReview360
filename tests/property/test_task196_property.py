import hypothesis.strategies as st
import pytest
from hypothesis import given

metadata = pytest.importorskip("docreview360.metadata")


@given(st.text())
def test_description_not_empty(text: str) -> None:
    assert metadata.normalize_description(text)
