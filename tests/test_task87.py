import pytest

from docuflow.stubs.task87 import task87


def test_task87_not_implemented() -> None:
    task87()
    pytest.fail("Task 87 not implemented")
