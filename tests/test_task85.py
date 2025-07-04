import pytest

from docuflow.stubs.task85 import task85


def test_task85_not_implemented() -> None:
    task85()
    pytest.fail("Task 85 not implemented")
