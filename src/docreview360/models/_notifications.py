# SPDX-License-Identifier: MIT
"""Notification models: VALID_NOTIFICATION_CHANNELS, DashboardVisibilityRecord, UserNotificationPreference."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from ._base import Base

# ---------------------------------------------------------------------------
# Per-user notification preferences (Item 44 Phase 2)
# ---------------------------------------------------------------------------

VALID_NOTIFICATION_CHANNELS = {"email", "slack", "teams", "webhook", "in_app"}


class DashboardVisibilityRecord(Base):
    """Per-user dashboard widget visibility preferences (Item 45 Phase 3)."""

    __tablename__ = "dashboard_visibility"

    username: Mapped[str] = mapped_column(String(255), primary_key=True)
    widgets: Mapped[dict] = mapped_column(JSON, default=dict)


class UserNotificationPreference(Base):
    """Per-user notification channel preference.

    Overrides the global notification settings for a specific user so that
    review lifecycle events reach them through their preferred channel.
    """

    __tablename__ = "user_notification_preferences"

    username: Mapped[str] = mapped_column(String(100), primary_key=True)
    # One of: email | slack | teams | webhook | in_app
    preferred_channel: Mapped[str] = mapped_column(String(50), default="email")
    # Optional per-user webhook URL (used when preferred_channel == "webhook")
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Optional email override (different address from the account email)
    email_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
