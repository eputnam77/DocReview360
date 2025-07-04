import pytest

from docuflow.stubs.task80 import task80


def test_task80_not_implemented() -> None:
    task80()
    pytest.fail("Task 80 not implemented")
