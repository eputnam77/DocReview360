"""Simple email notification helpers (task 31)."""

from __future__ import annotations

from typing import Dict, List


class Template:
    """Email template with ``subject`` and ``body`` placeholders."""

    def __init__(self, subject: str, body: str) -> None:
        self.subject = subject
        self.body = body


# registry of named templates
TEMPLATES: Dict[str, Template] = {"default": Template("{subject}", "{body}")}
# store sent emails for inspection in tests
sent_emails: List[dict[str, str]] = []


def add_template(name: str, subject: str, body: str) -> None:
    """Register a new template."""
    if not name:
        raise ValueError("name required")
    TEMPLATES[name] = Template(subject, body)


def send_email(template: str, recipient: str, **context: str) -> dict[str, str]:
    """Render ``template`` using ``context`` and store it in :data:`sent_emails`."""
    if not recipient:
        raise ValueError("recipient required")
    tmpl = TEMPLATES.get(template)
    if tmpl is None:
        raise KeyError(f"template '{template}' not found")
    try:
        subject = tmpl.subject.format(**context)
        body = tmpl.body.format(**context)
    except KeyError as exc:  # pragma: no cover - usage error
        raise ValueError(f"missing placeholder {exc.args[0]}") from exc
    email = {"to": recipient, "subject": subject, "body": body}
    sent_emails.append(email)
    return email


def notify_overdue_projects() -> list[dict[str, str]]:
    """Send alerts for overdue high priority projects."""
    from . import search

    emails: list[dict[str, str]] = []
    if "default" not in TEMPLATES:
        TEMPLATES["default"] = Template("{subject}", "{body}")
    for pid in search.overdue_high_priority():
        emails.append(
            send_email(
                "default",
                "admin@example.com",
                subject=f"Overdue project {pid}",
                body=pid,
            )
        )
    return emails
