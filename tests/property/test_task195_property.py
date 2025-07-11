import hypothesis.strategies as st
import pytest
from hypothesis import given

hooks = pytest.importorskip("docreview360.git_hooks")


@given(st.text())
def test_validate_patch_does_not_crash(patch):
    hooks.validate_patch(patch)
