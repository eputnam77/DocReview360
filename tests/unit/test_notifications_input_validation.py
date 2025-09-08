import pytest

import docreview360.notifications as n
import docreview360.search as search


def test_add_template_validates_subject_and_body():
    original = n.TEMPLATES.copy()
    try:
        with pytest.raises(TypeError):
            n.add_template("tmpl", subject=123, body="body")
        with pytest.raises(ValueError):
            n.add_template("tmpl2", subject="  ", body="body")
        with pytest.raises(TypeError):
            n.add_template("tmpl3", subject="sub", body=object())
        with pytest.raises(ValueError):
            n.add_template("tmpl4", subject="sub", body="   ")
    finally:
        n.TEMPLATES.clear()
        n.TEMPLATES.update(original)


def test_send_email_errors_and_defaults(monkeypatch):
    original = n.TEMPLATES.copy()
    n.sent_emails.clear()
    try:
        with pytest.raises(ValueError):
            n.send_email("default", "", subject="s", body="b")
        with pytest.raises(KeyError):
            n.send_email("missing", "u@example.com")
        with pytest.raises(ValueError):
            n.send_email("default", "u@example.com", subject="s")

        # remove templates to trigger auto-creation paths
        n.TEMPLATES.pop("due_reminder", None)
        n.TEMPLATES.pop("completion_notice", None)
        n.TEMPLATES.pop("default", None)
        monkeypatch.setattr(search, "overdue_high_priority", lambda: ["p1"])
        n.send_due_date_reminder("u@example.com", "doc", "2025-01-01")
        n.send_completion_notification("u@example.com", "doc")
        emails = n.notify_overdue_projects()
        assert emails[0]["subject"] == "Overdue project p1"
    finally:
        n.TEMPLATES.clear()
        n.TEMPLATES.update(original)
