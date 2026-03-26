"""Tests for notification template management edge cases."""

import docreview360.email_templates as et
import docreview360.notifications as n
import pytest


def test_add_template_refuses_overwrite(tmp_path) -> None:
    """Registering the same template twice should raise an error."""
    et.reset_email_templates(root=tmp_path / "email_templates.json")
    n.TEMPLATES.pop("greeting", None)
    n.add_template("greeting", "Hi {name}", "Hello {name}")
    try:
        with pytest.raises(ValueError):
            n.add_template("greeting", "Hi {name}", "Hello {name}")
    finally:
        n.TEMPLATES.pop("greeting", None)


def test_add_template_rejects_whitespace_name(tmp_path) -> None:
    """Names consisting only of whitespace are invalid."""
    et.reset_email_templates(root=tmp_path / "email_templates.json")
    with pytest.raises(ValueError):
        n.add_template("   ", "sub", "body")


def test_add_template_strips_name(tmp_path) -> None:
    """Leading/trailing whitespace should not create separate keys."""
    et.reset_email_templates(root=tmp_path / "email_templates.json")
    n.TEMPLATES.pop("hello", None)
    n.add_template("  hello  ", "Hi", "Body")
    try:
        assert "hello" in n.TEMPLATES and "  hello  " not in n.TEMPLATES
    finally:
        n.TEMPLATES.pop("hello", None)


def test_notification_helpers(monkeypatch, tmp_path) -> None:
    """Smoke test additional notification utilities."""
    et.reset_email_templates(root=tmp_path / "email_templates.json")
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
    assert subjects == ["item due 2024-01-01", "item complete"]
