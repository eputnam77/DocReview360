# SPDX-License-Identifier: MIT
"""Notification helpers — email, Slack, and Microsoft Teams."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from . import email_templates

_logger = logging.getLogger(__name__)


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
    except Exception as exc:
        # Avoid failing notification flows if persistence is unavailable.
        _logger.warning("Could not persist email template %r: %s", name, exc)
        return


def _resolve_template(name: str) -> Template:
    tmpl = None
    try:
        tmpl = email_templates.get_template(name)
    except Exception as exc:
        _logger.debug("Could not load persisted template %r: %s", name, exc)
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


# ---------------------------------------------------------------------------
# Slack / Microsoft Teams / generic webhook notifications
# ---------------------------------------------------------------------------

# Inspection lists for tests (mirror the sent_emails pattern)
sent_slack_notifications: List[Dict[str, str]] = []
sent_teams_notifications: List[Dict[str, str]] = []
sent_webhook_notifications: List[Dict[str, Any]] = []


def send_slack_notification(webhook_url: str, message: str) -> Dict[str, str]:
    """POST ``message`` to a Slack incoming-webhook URL.

    The Slack Incoming Webhooks API expects ``{"text": "<message>"}``
    (https://api.slack.com/messaging/webhooks).  Errors are logged and returned
    as ``{"error": "..."}`` rather than raised so a failing webhook never
    interrupts application flow.
    """
    if not isinstance(webhook_url, str) or not webhook_url.startswith("https://"):
        raise ValueError("webhook_url must be an https:// URL")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message is required")

    payload: Dict[str, str] = {"webhook_url": webhook_url, "message": message}
    try:
        from .http_client import post as _http_post

        resp = _http_post(webhook_url, json={"text": message})
        resp.raise_for_status()
        sent_slack_notifications.append(payload)
        return payload
    except Exception as exc:
        _logger.warning("Slack notification failed (url=%s): %s", webhook_url, exc)
        return {**payload, "error": str(exc)}


def send_teams_notification(webhook_url: str, message: str) -> Dict[str, str]:
    """POST ``message`` to a Microsoft Teams incoming-webhook URL.

    Teams uses the Adaptive Card schema
    (https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/
    how-to/add-incoming-webhook).  The minimal payload that renders a text message
    is an Adaptive Card body attached to a ``message`` activity.
    """
    if not isinstance(webhook_url, str) or not webhook_url.startswith("https://"):
        raise ValueError("webhook_url must be an https:// URL")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message is required")

    adaptive_card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [{"type": "TextBlock", "text": message, "wrap": True}],
                },
            }
        ],
    }
    payload: Dict[str, str] = {"webhook_url": webhook_url, "message": message}
    try:
        from .http_client import post as _http_post

        resp = _http_post(webhook_url, json=adaptive_card)
        resp.raise_for_status()
        sent_teams_notifications.append(payload)
        return payload
    except Exception as exc:
        _logger.warning("Teams notification failed (url=%s): %s", webhook_url, exc)
        return {**payload, "error": str(exc)}


def send_webhook_notification(webhook_url: str, event: str, **context: str) -> Dict[str, Any]:
    """POST a generic JSON event payload to ``webhook_url``.

    Useful for custom integrations that are not Slack or Teams.  The body is
    ``{"event": "<event>", **context}`` as a JSON object.
    """
    if not isinstance(webhook_url, str) or not webhook_url.startswith("https://"):
        raise ValueError("webhook_url must be an https:// URL")
    if not event or not event.strip():
        raise ValueError("event is required")

    body: Dict[str, Any] = {"event": event, **context}
    try:
        from .http_client import post as _http_post

        resp = _http_post(webhook_url, json=body)
        resp.raise_for_status()
        sent_webhook_notifications.append(body)
        return body
    except Exception as exc:
        _logger.warning("Webhook notification failed (url=%s): %s", webhook_url, exc)
        return {**body, "error": str(exc)}


def get_user_notification_preference(username: str) -> "Any | None":
    """Return the ``UserNotificationPreference`` record for *username*, or ``None``."""
    try:
        from .database import Database
        from .models import UserNotificationPreference
        import os

        db_url = os.environ.get("DOCREVIEW360_DB_URL", "sqlite:///docreview360.db")
        db = Database(db_url)
        db.migrate()
        with db.orm_session() as session:
            return session.get(UserNotificationPreference, username)
    except Exception as exc:
        _logger.debug("Could not fetch user notification preference for %s: %s", username, exc)
        return None


def save_user_notification_preference(
    username: str,
    preferred_channel: str,
    webhook_url: str | None = None,
    email_override: str | None = None,
) -> "Any":
    """Upsert a ``UserNotificationPreference`` record and return it."""
    from .models import VALID_NOTIFICATION_CHANNELS, UserNotificationPreference

    if preferred_channel not in VALID_NOTIFICATION_CHANNELS:
        raise ValueError(
            f"Invalid channel '{preferred_channel}'. "
            f"Valid values: {sorted(VALID_NOTIFICATION_CHANNELS)}"
        )
    if webhook_url is not None and not webhook_url.startswith("https://"):
        raise ValueError("webhook_url must be an https:// URL")

    import os
    from .database import Database

    db_url = os.environ.get("DOCREVIEW360_DB_URL", "sqlite:///docreview360.db")
    db = Database(db_url)
    db.migrate()
    with db.orm_session() as session:
        pref = session.get(UserNotificationPreference, username)
        if pref is None:
            pref = UserNotificationPreference(username=username)
            session.add(pref)
        pref.preferred_channel = preferred_channel
        pref.webhook_url = webhook_url
        pref.email_override = email_override
    # Re-fetch outside the session so it can be safely serialised by callers.
    with db.orm_session() as session:
        return session.get(UserNotificationPreference, username)


def send_notification(
    event: str,
    recipient_username: str | None = None,
    **context: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """Dispatch ``event`` to all enabled notification channels.

    Settings are read from ``settings_manager`` under the ``notifications``
    key.  Missing or malformed settings are silently ignored so this function
    is always safe to call even if the user has not configured notifications.

    When *recipient_username* is provided the function first looks up that
    user's ``UserNotificationPreference``.  If a preference exists the
    preferred channel is used instead of the global defaults, so each reviewer
    can receive notifications through their chosen channel.

    Returns a dict mapping channel name to the list of results produced by
    each delivery attempt.
    """
    try:
        from .settings_manager import load_settings

        ns: Dict[str, Any] = load_settings().get("notifications", {})
    except Exception as exc:  # pragma: no cover — settings not available
        _logger.warning("Could not load notification settings: %s", exc)
        ns = {}

    results: Dict[str, List[Dict[str, Any]]] = {"slack": [], "teams": [], "email": [], "webhook": []}
    message = context.get("message") or f"DocReview360 event: {event}"

    # ------------------------------------------------------------------
    # Per-user channel override
    # ------------------------------------------------------------------
    pref = None
    if recipient_username:
        pref = get_user_notification_preference(recipient_username)

    if pref is not None:
        channel = pref.preferred_channel
        if channel == "slack" and ns.get("slack_webhook_url"):
            results["slack"].append(send_slack_notification(ns["slack_webhook_url"], message))
        elif channel == "teams" and ns.get("teams_webhook_url"):
            results["teams"].append(send_teams_notification(ns["teams_webhook_url"], message))
        elif channel == "email":
            recipient_email = pref.email_override or ns.get("email_recipient")
            if recipient_email:
                if "default" not in TEMPLATES:
                    TEMPLATES["default"] = Template("{subject}", "{body}")
                results["email"].append(
                    send_email(
                        "default",
                        recipient_email,
                        subject=f"[DocReview360] {event}",
                        body=message,
                    )
                )
        elif channel == "webhook":
            webhook_url = pref.webhook_url or ns.get("webhook_url")
            if webhook_url:
                results["webhook"].append(send_webhook_notification(webhook_url, event, **context))
        # "in_app" is stored but has no outbound delivery; silently accepted.
        return results

    # ------------------------------------------------------------------
    # Global settings fallback (no per-user preference found)
    # ------------------------------------------------------------------
    if ns.get("slack_enabled") and ns.get("slack_webhook_url"):
        results["slack"].append(send_slack_notification(ns["slack_webhook_url"], message))

    if ns.get("teams_enabled") and ns.get("teams_webhook_url"):
        results["teams"].append(send_teams_notification(ns["teams_webhook_url"], message))

    if ns.get("email_enabled") and ns.get("email_recipient"):
        if "default" not in TEMPLATES:
            TEMPLATES["default"] = Template("{subject}", "{body}")
        results["email"].append(
            send_email("default", ns["email_recipient"], subject=f"[DocReview360] {event}", body=message)
        )

    if ns.get("webhook_enabled") and ns.get("webhook_url"):
        results["webhook"].append(send_webhook_notification(ns["webhook_url"], event, **context))

    return results
