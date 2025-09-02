"""Simple email notification helpers (task 31)."""

from __future__ import annotations

from typing import Dict, List


class Template:
    """Email template with ``subject`` and ``body`` placeholders."""

    def __init__(self, subject: str, body: str) -> None:
        self.subject = subject
        self.body = body


# registry of named templates
TEMPLATES: Dict[str, Template] = {
    "default": Template("{subject}", "{body}"),
    "due_reminder": Template("Reminder: {item} due {due_date}", "{item} is due on {due_date}."),
    "completion_notice": Template("{item} completed", "{item} has been completed."),
}
# store sent emails for inspection in tests
sent_emails: List[dict[str, str]] = []


def add_template(name: str, subject: str, body: str) -> None:
    """Register a new template."""
    # ``name`` may come from user input.  ``if not name`` would allow values
    # consisting solely of whitespace which produce awkward template keys such
    # as ``" "`` that are hard to reference later.  Normalise by requiring a
    # non-empty string after trimming.
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name required")
    name = name.strip()
    # Accidentally overwriting an existing template can lead to subtle bugs
    # in calling code that relies on a particular subject/body format.  The
    # previous implementation silently replaced any existing entry which meant
    # callers had no indication that a template name had already been used.
    # Instead of clobbering the old template, refuse the update so the caller
    # can make an explicit choice.
    if name in TEMPLATES:
        raise ValueError(f"template '{name}' already exists")
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
    except KeyError as exc:
        raise ValueError(f"missing placeholder {exc.args[0]}") from exc
    email = {"to": recipient, "subject": subject, "body": body}
    sent_emails.append(email)
    return email


def send_due_date_reminder(recipient: str, item: str, due_date: str) -> dict[str, str]:
    """Send a reminder that ``item`` is due on ``due_date``."""
    if "due_reminder" not in TEMPLATES:
        TEMPLATES["due_reminder"] = Template(
            "Reminder: {item} due {due_date}", "{item} is due on {due_date}."
        )
    return send_email("due_reminder", recipient, item=item, due_date=due_date)


def send_completion_notification(recipient: str, item: str) -> dict[str, str]:
    """Notify that ``item`` has been completed."""
    if "completion_notice" not in TEMPLATES:
        TEMPLATES["completion_notice"] = Template(
            "{item} completed", "{item} has been completed."
        )
    return send_email("completion_notice", recipient, item=item)


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
