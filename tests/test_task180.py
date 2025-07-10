import pytest

from docuflow.stubs.task180 import task180


def test_task180_placeholder() -> None:
    """Placeholder failing test for task 180."""
    task180()
    pytest.fail("Task 180 not implemented")
