# SPDX-License-Identifier: MIT
"""Notifications sub-router: GET/PUT /notifications/settings and per-user preferences."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth
from ..models import VALID_NOTIFICATION_CHANNELS
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


# ---------------------------------------------------------------------------
# Per-user notification preferences (Item 44 Phase 2)
# ---------------------------------------------------------------------------


class UserNotificationPreferenceSchema(BaseModel):
    """Pydantic schema for a user's notification channel preference."""

    username: str
    preferred_channel: str = "email"
    webhook_url: str | None = None
    email_override: str | None = None


class UserNotificationPreferenceUpdate(BaseModel):
    """Request body for updating a user's notification preference."""

    preferred_channel: str = "email"
    webhook_url: str | None = None
    email_override: str | None = None


def _pref_to_schema(pref: Any) -> UserNotificationPreferenceSchema:
    return UserNotificationPreferenceSchema(
        username=pref.username,
        preferred_channel=pref.preferred_channel,
        webhook_url=pref.webhook_url,
        email_override=pref.email_override,
    )


def _default_pref(username: str) -> UserNotificationPreferenceSchema:
    return UserNotificationPreferenceSchema(username=username)


@router.get(
    "/notifications/preferences/me",
    response_model=UserNotificationPreferenceSchema,
)
async def get_my_notification_preference(
    current_user: auth.User = Depends(auth.get_current_user),
) -> UserNotificationPreferenceSchema:
    """Return the current user's notification channel preference."""
    from ..notifications import get_user_notification_preference

    pref = get_user_notification_preference(current_user.username)
    if pref is None:
        return _default_pref(current_user.username)
    return _pref_to_schema(pref)


@router.put(
    "/notifications/preferences/me",
    response_model=UserNotificationPreferenceSchema,
)
async def update_my_notification_preference(
    body: UserNotificationPreferenceUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> UserNotificationPreferenceSchema:
    """Update the current user's notification channel preference."""
    if body.preferred_channel not in VALID_NOTIFICATION_CHANNELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid channel '{body.preferred_channel}'. "
                f"Valid values: {sorted(VALID_NOTIFICATION_CHANNELS)}"
            ),
        )
    if body.webhook_url is not None and not body.webhook_url.startswith("https://"):
        raise HTTPException(status_code=422, detail="webhook_url must be an https:// URL")
    from ..notifications import save_user_notification_preference

    try:
        pref = save_user_notification_preference(
            current_user.username,
            body.preferred_channel,
            webhook_url=body.webhook_url,
            email_override=body.email_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _pref_to_schema(pref)


@router.get(
    "/notifications/preferences/{username}",
    response_model=UserNotificationPreferenceSchema,
)
async def get_user_pref(
    username: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> UserNotificationPreferenceSchema:
    """Return the notification preference for *username*.

    A user may read their own preference; admins can read any user's preference.
    """
    from .. import rbac as _rbac
    from ..notifications import get_user_notification_preference

    is_admin = "admin" in _rbac.get_roles(current_user.username)
    if username != current_user.username and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorised to view this preference")
    pref = get_user_notification_preference(username)
    if pref is None:
        return _default_pref(username)
    return _pref_to_schema(pref)


@router.put(
    "/notifications/preferences/{username}",
    response_model=UserNotificationPreferenceSchema,
)
async def update_user_pref(
    username: str,
    body: UserNotificationPreferenceUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> UserNotificationPreferenceSchema:
    """Update the notification preference for *username*.

    A user may update their own preference; admins can update any user's preference.
    """
    from .. import rbac as _rbac
    from ..notifications import save_user_notification_preference

    is_admin = "admin" in _rbac.get_roles(current_user.username)
    if username != current_user.username and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorised to update this preference")
    if body.preferred_channel not in VALID_NOTIFICATION_CHANNELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid channel '{body.preferred_channel}'. "
                f"Valid values: {sorted(VALID_NOTIFICATION_CHANNELS)}"
            ),
        )
    if body.webhook_url is not None and not body.webhook_url.startswith("https://"):
        raise HTTPException(status_code=422, detail="webhook_url must be an https:// URL")
    try:
        pref = save_user_notification_preference(
            username,
            body.preferred_channel,
            webhook_url=body.webhook_url,
            email_override=body.email_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _pref_to_schema(pref)
