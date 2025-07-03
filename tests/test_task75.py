import pytest

from docuflow.stubs.task75 import task75


def test_task75_not_implemented() -> None:
    task75()
    pytest.fail("Task 75 not implemented")
