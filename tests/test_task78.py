import pytest

from docuflow.stubs.task78 import task78


def test_task78_not_implemented() -> None:
    task78()
    pytest.fail("Task 78 not implemented")
