# SPDX-License-Identifier: MIT
"""Item 44 Phase 2 — Per-user notification channel preferences.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item44_notification_prefs.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import patch

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    from docreview360 import rbac
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _bob_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "bob",
            auth.DEMO_USER_DEFAULTS["bob"]["password"],
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _charlie_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user("charlie", "charlie123")
    except Exception:
        pass
    token = auth.create_access_token({"sub": "charlie"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit tests for notifications helpers
# ---------------------------------------------------------------------------


class TestNotificationPreferenceHelpers:
    """Unit tests for get/save_user_notification_preference."""

    def test_get_preference_returns_none_for_unknown_user(self) -> None:
        from docreview360.notifications import get_user_notification_preference

        pref = get_user_notification_preference("unknown_user_xyz")
        assert pref is None

    def test_save_and_get_preference(self) -> None:
        from docreview360.notifications import (
            get_user_notification_preference,
            save_user_notification_preference,
        )

        save_user_notification_preference("pref_test_user", "slack")
        pref = get_user_notification_preference("pref_test_user")
        assert pref is not None
        assert pref.username == "pref_test_user"
        assert pref.preferred_channel == "slack"
        assert pref.webhook_url is None
        assert pref.email_override is None

    def test_save_preference_all_channels(self) -> None:
        from docreview360.notifications import save_user_notification_preference

        for channel in ("email", "slack", "teams", "webhook", "in_app"):
            save_user_notification_preference(f"ch_test_{channel}", channel)

    def test_save_preference_invalid_channel_raises(self) -> None:
        from docreview360.notifications import save_user_notification_preference

        with pytest.raises(ValueError, match="Invalid channel"):
            save_user_notification_preference("bad_ch_user", "fax")

    def test_save_preference_with_webhook_url(self) -> None:
        from docreview360.notifications import (
            get_user_notification_preference,
            save_user_notification_preference,
        )

        save_user_notification_preference(
            "wh_user",
            "webhook",
            webhook_url="https://hooks.example.com/mine",
        )
        pref = get_user_notification_preference("wh_user")
        assert pref is not None
        assert pref.preferred_channel == "webhook"
        assert pref.webhook_url == "https://hooks.example.com/mine"

    def test_save_preference_webhook_url_must_be_https(self) -> None:
        from docreview360.notifications import save_user_notification_preference

        with pytest.raises(ValueError, match="https://"):
            save_user_notification_preference(
                "bad_wh_user", "webhook", webhook_url="http://insecure.example.com"
            )

    def test_save_preference_with_email_override(self) -> None:
        from docreview360.notifications import (
            get_user_notification_preference,
            save_user_notification_preference,
        )

        save_user_notification_preference(
            "email_override_user",
            "email",
            email_override="other@example.com",
        )
        pref = get_user_notification_preference("email_override_user")
        assert pref is not None
        assert pref.email_override == "other@example.com"

    def test_save_preference_upserts(self) -> None:
        from docreview360.notifications import (
            get_user_notification_preference,
            save_user_notification_preference,
        )

        save_user_notification_preference("upsert_user", "email")
        save_user_notification_preference("upsert_user", "teams")
        pref = get_user_notification_preference("upsert_user")
        assert pref is not None
        assert pref.preferred_channel == "teams"


# ---------------------------------------------------------------------------
# Unit tests for send_notification with per-user preferences
# ---------------------------------------------------------------------------


class TestSendNotificationWithPreferences:
    """send_notification() routes to per-user channel when preference exists."""

    def test_send_notification_falls_back_to_global_when_no_preference(self) -> None:
        """No per-user preference: global settings still govern dispatch."""
        from docreview360.notifications import send_notification, sent_emails

        initial_count = len(sent_emails)
        # No preference set for this user; no global settings configured either.
        results = send_notification("test.event", recipient_username="no_pref_user_abc")
        assert isinstance(results, dict)
        assert "email" in results
        # Nothing sent because neither global settings nor per-user prefs are set.
        assert len(sent_emails) == initial_count

    def test_send_notification_uses_per_user_email_channel(self) -> None:
        from docreview360.notifications import (
            save_user_notification_preference,
            send_notification,
            sent_emails,
        )

        save_user_notification_preference(
            "email_pref_user",
            "email",
            email_override="reviewer@example.com",
        )
        before = len(sent_emails)
        send_notification("review.assigned", recipient_username="email_pref_user", message="Hello")
        # Email should be dispatched to the override address.
        new_emails = sent_emails[before:]
        assert len(new_emails) == 1
        assert new_emails[0]["to"] == "reviewer@example.com"

    def test_send_notification_uses_per_user_webhook_channel(self) -> None:
        from docreview360.notifications import (
            save_user_notification_preference,
            send_notification,
            sent_webhook_notifications,
        )

        save_user_notification_preference(
            "wh_pref_user",
            "webhook",
            webhook_url="https://hooks.example.com/wh_pref_user",
        )
        before = len(sent_webhook_notifications)
        with patch("docreview360.http_client.post") as mock_post:
            mock_post.return_value.raise_for_status = lambda: None
            send_notification("review.reminder", recipient_username="wh_pref_user", message="Remind")
        after = len(sent_webhook_notifications)
        assert after > before

    def test_send_notification_in_app_channel_no_outbound(self) -> None:
        """in_app channel: accepted without error, no outbound delivery."""
        from docreview360.notifications import (
            save_user_notification_preference,
            send_notification,
            sent_emails,
            sent_slack_notifications,
            sent_teams_notifications,
            sent_webhook_notifications,
        )

        save_user_notification_preference("in_app_user", "in_app")
        s_before = len(sent_slack_notifications)
        t_before = len(sent_teams_notifications)
        e_before = len(sent_emails)
        w_before = len(sent_webhook_notifications)
        results = send_notification("review.signed", recipient_username="in_app_user", message="Hi")
        assert isinstance(results, dict)
        # No outbound delivery expected for in_app channel.
        assert len(sent_slack_notifications) == s_before
        assert len(sent_teams_notifications) == t_before
        assert len(sent_emails) == e_before
        assert len(sent_webhook_notifications) == w_before

    def test_send_notification_slack_channel_uses_global_webhook(self) -> None:
        """slack channel preference falls back to global slack_webhook_url."""
        from docreview360 import settings_manager
        from docreview360.notifications import (
            save_user_notification_preference,
            send_notification,
            sent_slack_notifications,
        )

        settings_manager.update_setting(
            "notifications",
            {
                "slack_enabled": True,
                "slack_webhook_url": "https://hooks.slack.com/test123",
                "teams_enabled": False,
                "email_enabled": False,
                "webhook_enabled": False,
            },
        )
        save_user_notification_preference("slack_pref_user", "slack")
        before = len(sent_slack_notifications)
        with patch("docreview360.http_client.post") as mock_post:
            mock_post.return_value.raise_for_status = lambda: None
            send_notification("review.assigned", recipient_username="slack_pref_user", message="Hi")
        assert len(sent_slack_notifications) > before

    def test_send_notification_no_recipient_username_uses_global(self) -> None:
        """When recipient_username is omitted global settings are used."""
        from docreview360.notifications import send_notification

        results = send_notification("test.event", message="No recipient")
        assert isinstance(results, dict)
        assert set(results.keys()) >= {"slack", "teams", "email", "webhook"}


# ---------------------------------------------------------------------------
# API endpoint tests — GET /notifications/preferences/me
# ---------------------------------------------------------------------------


class TestGetMyPreferenceEndpoint:
    """Tests for GET /notifications/preferences/me."""

    def setup_method(self) -> None:
        """Reset alice's preference to 'email' before every GET test to avoid
        state pollution from TestUpdateMyPreferenceEndpoint which runs first and
        leaves alice on the last channel in the iteration (currently 'in_app')."""
        from docreview360.notifications import save_user_notification_preference

        save_user_notification_preference("alice", "email")

    def test_get_my_preference_returns_default_for_new_user(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/notifications/preferences/me", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["preferred_channel"] == "email"
        assert data["webhook_url"] is None
        assert data["email_override"] is None

    def test_get_my_preference_requires_auth(self) -> None:
        client = TestClient(app)
        resp = client.get("/notifications/preferences/me")
        assert resp.status_code in (401, 403)

    def test_get_my_preference_reflects_saved_value(self) -> None:
        from docreview360.notifications import save_user_notification_preference

        save_user_notification_preference("alice", "teams")
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/notifications/preferences/me", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["preferred_channel"] == "teams"
        # Reset alice back to email for subsequent tests.
        save_user_notification_preference("alice", "email")


# ---------------------------------------------------------------------------
# API endpoint tests — PUT /notifications/preferences/me
# ---------------------------------------------------------------------------


class TestUpdateMyPreferenceEndpoint:
    """Tests for PUT /notifications/preferences/me."""

    def test_update_my_preference_changes_channel(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.put(
            "/notifications/preferences/me",
            json={"preferred_channel": "slack"},
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["preferred_channel"] == "slack"
        assert data["username"] == "alice"

    def test_update_my_preference_invalid_channel_returns_422(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.put(
            "/notifications/preferences/me",
            json={"preferred_channel": "pigeon_post"},
            headers=hdrs,
        )
        assert resp.status_code == 422

    def test_update_my_preference_with_webhook_url(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.put(
            "/notifications/preferences/me",
            json={
                "preferred_channel": "webhook",
                "webhook_url": "https://hooks.example.com/alice",
            },
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["preferred_channel"] == "webhook"
        assert data["webhook_url"] == "https://hooks.example.com/alice"

    def test_update_my_preference_webhook_url_http_returns_422(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.put(
            "/notifications/preferences/me",
            json={
                "preferred_channel": "webhook",
                "webhook_url": "http://insecure.example.com/hook",
            },
            headers=hdrs,
        )
        assert resp.status_code == 422

    def test_update_my_preference_with_email_override(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.put(
            "/notifications/preferences/me",
            json={
                "preferred_channel": "email",
                "email_override": "alice.work@example.com",
            },
            headers=hdrs,
        )
        assert resp.status_code == 200
        assert resp.json()["email_override"] == "alice.work@example.com"

    def test_update_my_preference_all_valid_channels(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        for channel in ("email", "slack", "teams", "webhook", "in_app"):
            resp = client.put(
                "/notifications/preferences/me",
                json={"preferred_channel": channel},
                headers=hdrs,
            )
            assert resp.status_code == 200, f"Channel '{channel}' should be valid"

    def test_update_my_preference_requires_auth(self) -> None:
        client = TestClient(app)
        resp = client.put(
            "/notifications/preferences/me",
            json={"preferred_channel": "slack"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# API endpoint tests — GET /notifications/preferences/{username}
# ---------------------------------------------------------------------------


class TestGetUserPreferenceEndpoint:
    """Tests for GET /notifications/preferences/{username}."""

    def test_admin_can_get_any_user_preference(self) -> None:
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        resp = client.get("/notifications/preferences/bob", headers=alice_hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "bob"

    def test_user_can_get_own_preference(self) -> None:
        client = TestClient(app)
        bob_hdrs = _bob_headers()
        resp = client.get("/notifications/preferences/bob", headers=bob_hdrs)
        assert resp.status_code == 200
        assert resp.json()["username"] == "bob"

    def test_non_admin_cannot_get_other_user_preference(self) -> None:
        client = TestClient(app)
        bob_hdrs = _bob_headers()
        charlie_hdrs = _charlie_headers()
        # bob tries to read charlie's prefs
        resp = client.get("/notifications/preferences/charlie", headers=bob_hdrs)
        assert resp.status_code == 403

    def test_get_preference_requires_auth(self) -> None:
        client = TestClient(app)
        resp = client.get("/notifications/preferences/alice")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# API endpoint tests — PUT /notifications/preferences/{username}
# ---------------------------------------------------------------------------


class TestUpdateUserPreferenceEndpoint:
    """Tests for PUT /notifications/preferences/{username}."""

    def test_admin_can_update_other_user_preference(self) -> None:
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        _bob_headers()  # ensure bob exists
        resp = client.put(
            "/notifications/preferences/bob",
            json={"preferred_channel": "teams"},
            headers=alice_hdrs,
        )
        assert resp.status_code == 200
        assert resp.json()["preferred_channel"] == "teams"

    def test_user_can_update_own_preference(self) -> None:
        client = TestClient(app)
        bob_hdrs = _bob_headers()
        resp = client.put(
            "/notifications/preferences/bob",
            json={"preferred_channel": "slack"},
            headers=bob_hdrs,
        )
        assert resp.status_code == 200
        assert resp.json()["preferred_channel"] == "slack"

    def test_non_admin_cannot_update_other_user_preference(self) -> None:
        client = TestClient(app)
        bob_hdrs = _bob_headers()
        _charlie_headers()  # ensure charlie exists
        resp = client.put(
            "/notifications/preferences/charlie",
            json={"preferred_channel": "teams"},
            headers=bob_hdrs,
        )
        assert resp.status_code == 403

    def test_update_user_pref_invalid_channel_returns_422(self) -> None:
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        resp = client.put(
            "/notifications/preferences/alice",
            json={"preferred_channel": "smoke_signals"},
            headers=alice_hdrs,
        )
        assert resp.status_code == 422
