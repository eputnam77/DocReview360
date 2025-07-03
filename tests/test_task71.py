import pytest

from docuflow.stubs.task71 import task71


def test_task71_not_implemented() -> None:
    task71()
    pytest.fail("Task 71 not implemented")
