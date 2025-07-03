import pytest

from docuflow.stubs.task70 import task70


def test_task70_not_implemented() -> None:
    task70()
    pytest.fail("Task 70 not implemented")
