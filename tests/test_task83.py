import pytest

from docuflow.stubs.task83 import task83


def test_task83_not_implemented() -> None:
    task83()
    pytest.fail("Task 83 not implemented")
