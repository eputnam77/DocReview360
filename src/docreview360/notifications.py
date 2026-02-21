"""Simple email notification helpers (task 31)."""

from __future__ import annotations

from typing import Dict, List

from . import email_templates


class Template:
    """Email template with ``subject`` and ``body`` placeholders."""

    def __init__(self, subject: str, body: str) -> None:
        self.subject = subject
        self.body = body


# registry of named templates
TEMPLATES: Dict[str, Template] = {
    "default": Template("{subject}", "{body}"),
    "due_reminder": Template("{item} due {due_date}", "Due {due_date}: {item}."),
    "completion_notice": Template("{item} complete", "Completed: {item}."),
}
# store sent emails for inspection in tests
sent_emails: List[dict[str, str]] = []


def _ensure_email_template(name: str, subject: str, body: str, task: str | None = None) -> None:
    """Ensure a persisted email template exists, without overwriting admin edits."""
    try:
        if email_templates.get_template(name) is None:
            email_templates.create_template(name, subject, body, task=task)
    except Exception:
        # Avoid failing notification flows if persistence is unavailable.
        return


def _resolve_template(name: str) -> Template:
    tmpl = None
    try:
        tmpl = email_templates.get_template(name)
    except Exception:
        tmpl = None
    if tmpl is not None:
        return Template(tmpl.subject, tmpl.body)
    local = TEMPLATES.get(name)
    if local is None:
        raise KeyError(f"template '{name}' not found")
    return local


def add_template(name: str, subject: str, body: str) -> None:
    """Register a new template."""
    # ``name`` may come from user input.  ``if not name`` would allow values
    # consisting solely of whitespace which produce awkward template keys such
    # as ``" "`` that are hard to reference later.  Normalize by requiring a
    # non-empty string after trimming.
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name required")
    if not isinstance(subject, str):
        raise TypeError("subject must be a string")
    if not subject.strip():
        raise ValueError("subject required")
    if not isinstance(body, str):
        raise TypeError("body must be a string")
    if not body.strip():
        raise ValueError("body required")
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
    _ensure_email_template(name, subject, body)


def send_email(template: str, recipient: str, **context: str) -> dict[str, str]:
    """Render ``template`` using ``context`` and store it in :data:`sent_emails`."""
    if not isinstance(template, str):
        raise TypeError("template must be a string")
    if not isinstance(recipient, str):
        raise TypeError("recipient must be a string")
    recipient = recipient.strip()
    if not recipient:
        raise ValueError("recipient required")
    tmpl_name = template.strip()
    if not tmpl_name:
        raise ValueError("template required")
    tmpl = _resolve_template(tmpl_name)
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
            "{item} due {due_date}", "Due {due_date}: {item}."
        )
    _ensure_email_template(
        "due_reminder",
        "{item} due {due_date}",
        "Due {due_date}: {item}.",
        task="reminder",
    )
    return send_email("due_reminder", recipient, item=item, due_date=due_date)


def send_completion_notification(recipient: str, item: str) -> dict[str, str]:
    """Notify that ``item`` has been completed."""
    if "completion_notice" not in TEMPLATES:
        TEMPLATES["completion_notice"] = Template("{item} complete", "Completed: {item}.")
    _ensure_email_template("completion_notice", "{item} complete", "Completed: {item}.", task="notification")
    return send_email("completion_notice", recipient, item=item)


def notify_overdue_projects() -> list[dict[str, str]]:
    """Send alerts for overdue high priority projects."""
    from . import search

    emails: list[dict[str, str]] = []
    if "default" not in TEMPLATES:
        TEMPLATES["default"] = Template("{subject}", "{body}")
    _ensure_email_template("default", "{subject}", "{body}", task="system")
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
