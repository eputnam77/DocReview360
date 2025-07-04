import pytest

from docuflow.stubs.task88 import task88


def test_task88_not_implemented() -> None:
    task88()
    pytest.fail("Task 88 not implemented")
