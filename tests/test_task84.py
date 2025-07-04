import pytest

from docuflow.stubs.task84 import task84


def test_task84_not_implemented() -> None:
    task84()
    pytest.fail("Task 84 not implemented")
