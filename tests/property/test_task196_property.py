import hypothesis.strategies as st
import pytest
from hypothesis import given

metadata = pytest.importorskip("docuflow.metadata")


@given(st.text())
def test_description_not_empty(text):
    assert metadata.normalize_description(text)
