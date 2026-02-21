from docreview360.notifications import (
    send_completion_notification,
    send_due_date_reminder,
    sent_emails,
)


def test_due_date_and_completion_notifications() -> None:
    sent_emails.clear()
    send_due_date_reminder("user@example.com", "Spec Review", "2025-01-01")
    send_completion_notification("user@example.com", "Spec Review")
    assert sent_emails[0]["subject"] == "Spec Review due 2025-01-01"
    assert sent_emails[1]["subject"] == "Spec Review complete"
