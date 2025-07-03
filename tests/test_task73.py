import pytest

from docuflow.stubs.task73 import task73


def test_task73_not_implemented() -> None:
    task73()
    pytest.fail("Task 73 not implemented")
