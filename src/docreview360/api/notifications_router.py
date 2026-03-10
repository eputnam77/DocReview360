# SPDX-License-Identifier: MIT
"""Notifications sub-router: GET/PUT /notifications/settings."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth
from ..rbac import require_role

_logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationSettings(BaseModel):
    """Configuration for outbound notifications."""

    slack_enabled: bool = False
    slack_webhook_url: str | None = None
    teams_enabled: bool = False
    teams_webhook_url: str | None = None
    email_enabled: bool = False
    email_recipient: str | None = None
    webhook_enabled: bool = False
    webhook_url: str | None = None


def _load_notification_settings() -> NotificationSettings:
    """Return current notification settings from ``settings_manager``."""
    try:
        from ..settings_manager import load_settings

        raw: Dict[str, Any] = load_settings().get("notifications", {})
        return NotificationSettings(**raw)
    except Exception as exc:
        _logger.warning("Could not load notification settings: %s", exc)
        return NotificationSettings()


def _save_notification_settings(settings: NotificationSettings) -> None:
    """Persist ``settings`` under the ``notifications`` key in ``settings_manager``."""
    from ..settings_manager import update_setting

    update_setting("notifications", settings.model_dump())


@router.get("/notifications/settings", response_model=NotificationSettings)
async def get_notification_settings(
    current_user: auth.User = Depends(auth.get_current_user),
) -> NotificationSettings:
    """Return the current notification channel settings."""
    return _load_notification_settings()


@router.put("/notifications/settings", response_model=NotificationSettings)
async def update_notification_settings(
    body: NotificationSettings,
    current_user: auth.User = Depends(require_role("admin")),
) -> NotificationSettings:
    """Update notification channel settings (admin only).

    Webhook URLs must start with ``https://``.  Validation errors are returned
    as HTTP 422.
    """
    for field_name, url in [
        ("slack_webhook_url", body.slack_webhook_url),
        ("teams_webhook_url", body.teams_webhook_url),
        ("webhook_url", body.webhook_url),
    ]:
        if url is not None and not url.startswith("https://"):
            raise HTTPException(
                status_code=422,
                detail=f"{field_name} must be an https:// URL",
            )

    try:
        _save_notification_settings(body)
    except Exception as exc:
        _logger.error("Failed to persist notification settings: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save notification settings") from exc

    return body


@router.post("/notifications/test")
async def test_notification(
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, object]:
    """Send a test notification to all enabled channels (admin only)."""
    from ..notifications import send_notification

    results = send_notification(
        "test",
        message="This is a DocReview360 test notification.",
        user=current_user.username,
    )
    return {"results": results}
