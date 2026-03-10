# SPDX-License-Identifier: MIT
"""Log-based alert helpers with notification integration."""

from __future__ import annotations

from collections import Counter
from typing import Dict

from .logs import LogEntry, log_event, register_alert
from .notifications import send_email

# Store Slack messages for inspection in tests
sent_slack_messages: list[Dict[str, str]] = []


def send_slack_message(channel: str, text: str) -> Dict[str, str]:
    """Record a Slack message destined for ``channel`` with ``text``."""
    message = {"channel": channel, "text": text}
    sent_slack_messages.append(message)
    return message


def _notify(
    alert_type: str,
    entry: LogEntry,
    *,
    email: str | None,
    slack: str | None,
) -> None:
    """Send notifications and log the alert event."""
    if email:
        send_email(
            "default",
            email,
            subject=f"{alert_type} detected",
            body=entry.action,
        )
    if slack:
        send_slack_message(slack, f"{alert_type} detected: {entry.action}")
    log_event(
        f"alert_{alert_type}",
        user_id=entry.user_id,
        entity_id=entry.entity_id,
        severity="warning",
        alert_type=alert_type,
        original_action=entry.action,
    )


def register_mass_approval_alert(
    *, threshold: int = 10, email: str | None = None, slack: str | None = None
) -> None:
    """Trigger when approvals exceed ``threshold`` for a user."""
    counts: Counter[str] = Counter()

    def callback(entry: LogEntry) -> None:
        user = entry.user_id or "unknown"
        counts[user] += 1
        if counts[user] >= threshold:
            _notify("mass_approval", entry, email=email, slack=slack)
            counts[user] = 0

    register_alert("approval_granted", callback)


def register_failed_login_alert(
    *, threshold: int = 5, email: str | None = None, slack: str | None = None
) -> None:
    """Trigger when failed logins exceed ``threshold`` for a user."""
    counts: Counter[str] = Counter()

    def callback(entry: LogEntry) -> None:
        user = entry.user_id or "unknown"
        counts[user] += 1
        if counts[user] >= threshold:
            _notify("failed_login", entry, email=email, slack=slack)
            counts[user] = 0

    register_alert("login_failed", callback)
