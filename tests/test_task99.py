import pytest

from docuflow.stubs.task99 import task99


def test_task99_placeholder() -> None:
    """Placeholder test for task 99."""
    task99()
    pytest.fail("Task 99 implementation missing")
