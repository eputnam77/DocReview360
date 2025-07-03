import pytest
from hypothesis import given
from hypothesis import strategies as st

from docuflow.stubs.task71 import task71


@given(st.none())
def test_task71_property(_) -> None:
    task71()
    pytest.fail("Task 71 not implemented")
