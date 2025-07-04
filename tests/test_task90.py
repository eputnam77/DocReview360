import pytest

from docuflow.stubs.task90 import task90


def test_task90_not_implemented() -> None:
    task90()
    pytest.fail("Task 90 not implemented")
