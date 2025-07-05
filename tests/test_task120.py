import pytest

from docuflow.stubs.task120 import task120


def test_task120_placeholder() -> None:
    """Placeholder test for task 120."""
    task120()
    pytest.fail("Task 120 implementation missing")
