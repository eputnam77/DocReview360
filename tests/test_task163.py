import pytest

from docuflow.stubs.task163 import render_extension_menu


def test_task163_extension_menu_placeholder() -> None:
    """Placeholder failing test for TipTap extension menu."""
    render_extension_menu(["Bold"])  # ensure callable
    pytest.skip("Task 163 not implemented: extension menu UI missing")
