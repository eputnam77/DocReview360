import hypothesis.strategies as st
import pytest
from hypothesis import given

util = pytest.importorskip("docreview360.deploy")


@given(st.integers())
def test_port_passthrough(port: int) -> None:
    assert util.normalize_port(port) >= 0
