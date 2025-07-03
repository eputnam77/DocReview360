import pytest

from docuflow.stubs.task72 import task72


def test_task72_not_implemented() -> None:
    task72()
    pytest.fail("Task 72 not implemented")
