from datetime import datetime, timedelta

from docuflow.notifications import notify_overdue_projects, sent_emails
from docuflow.search import ProjectModel, overdue_high_priority, projects


def test_overdue_high_priority_detection() -> None:
    proj = ProjectModel(
        id="pX",
        name="Important",
        priority=5,
        created=datetime.utcnow() - timedelta(days=20),
    )
    projects[proj.id] = proj
    assert proj.id in overdue_high_priority()
    sent_emails.clear()
    emails = notify_overdue_projects()
    assert any(proj.id in e["body"] for e in emails)
