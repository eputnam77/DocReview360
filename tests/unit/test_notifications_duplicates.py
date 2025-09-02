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


def test_add_template_rejects_whitespace_name() -> None:
    """Names consisting only of whitespace are invalid."""
    with pytest.raises(ValueError):
        n.add_template("   ", "sub", "body")


def test_add_template_strips_name() -> None:
    """Leading/trailing whitespace should not create separate keys."""
    n.TEMPLATES.pop("hello", None)
    n.add_template("  hello  ", "Hi", "Body")
    try:
        assert "hello" in n.TEMPLATES and "  hello  " not in n.TEMPLATES
    finally:
        n.TEMPLATES.pop("hello", None)


def test_notification_helpers(monkeypatch) -> None:
    """Smoke test additional notification utilities."""
    # Patch search.overdue_high_priority to provide deterministic ids
    import docreview360.search as search

    monkeypatch.setattr(search, "overdue_high_priority", lambda: ["p1"])
    n.sent_emails.clear()
    emails = n.notify_overdue_projects()
    assert emails[0]["subject"] == "Overdue project p1"

    n.sent_emails.clear()
    n.send_due_date_reminder("u@example.com", "item", "2024-01-01")
    n.send_completion_notification("u@example.com", "item")
    subjects = [e["subject"] for e in n.sent_emails]
    assert subjects == ["Reminder: item due 2024-01-01", "item completed"]
