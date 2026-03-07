from pathlib import Path
from uuid import uuid4

from docreview360 import email_templates
from docreview360.notifications import (
    TEMPLATES,
    send_completion_notification,
    send_due_date_reminder,
    sent_emails,
)


def test_due_date_and_completion_notifications() -> None:
    base = Path(".tmp") / f"notif-{uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    email_templates.reset_email_templates(root=base / "email_templates.json")
    TEMPLATES.pop("due_reminder", None)
    TEMPLATES.pop("completion_notice", None)
    sent_emails.clear()
    send_due_date_reminder("user@example.com", "Spec Review", "2025-01-01")
    send_completion_notification("user@example.com", "Spec Review")
    assert sent_emails[0]["subject"] == "Spec Review due 2025-01-01"
    assert sent_emails[1]["subject"] == "Spec Review complete"
