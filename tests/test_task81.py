import pytest

from docuflow.stubs.task81 import task81


def test_task81_not_implemented() -> None:
    task81()
    pytest.fail("Task 81 not implemented")
