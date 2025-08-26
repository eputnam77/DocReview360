"""Tests for notification template management edge cases."""

import pytest

import docreview360.notifications as n


def test_add_template_refuses_overwrite() -> None:
    """Registering the same template twice should raise an error."""
    n.TEMPLATES.pop("greeting", None)
    n.add_template("greeting", "Hi {name}", "Hello {name}")
    try:
        with pytest.raises(ValueError):
            n.add_template("greeting", "Hi {name}", "Hello {name}")
    finally:
        n.TEMPLATES.pop("greeting", None)
