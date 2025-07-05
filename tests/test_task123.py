import pytest

from docuflow.stubs.task123 import task123


def test_task123_placeholder() -> None:
    """Placeholder test for task 123."""
    task123()
    pytest.fail("Task 123 implementation missing")
