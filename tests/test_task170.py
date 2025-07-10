import pytest

from docuflow.stubs.task170 import task170


def test_task170_placeholder() -> None:
    """Placeholder failing test for task 170."""
    task170()
    pytest.fail("Task 170 not implemented")
