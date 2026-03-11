# SPDX-License-Identifier: MIT
"""Item 45 Phase 3 — Dashboard widget visibility preferences migrated to SQLite.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item45_visibility.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta

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


# ---------------------------------------------------------------------------
# Unit tests for dashboard_prefs module
# ---------------------------------------------------------------------------


class TestDashboardPrefsUnit:
    """Unit tests exercising get_visibility / set_visibility directly."""

    def test_get_visibility_returns_defaults_when_no_record(self) -> None:
        from docreview360.dashboard_prefs import DEFAULT_VISIBILITY, get_visibility

        result = get_visibility("testuser_no_record_xyz")
        for key, default_val in DEFAULT_VISIBILITY.items():
            assert result[key] == default_val, f"key={key} should be default"
        assert "widgets" in result
        assert result["widgets"] == []

    def test_set_visibility_persists_to_db(self) -> None:
        from docreview360.dashboard_prefs import set_visibility

        result = set_visibility(
            "testuser_set_xyz",
            {"stats": False, "widgets": ["kpi", "activity"]},
        )
        assert result["stats"] is False
        assert "widgets" in result
        assert result["widgets"] == ["kpi", "activity"]

    def test_get_visibility_after_set_returns_updated_state(self) -> None:
        from docreview360.dashboard_prefs import get_visibility, set_visibility

        user = "testuser_roundtrip_xyz"
        set_visibility(user, {"stats": False, "activity": False, "widgets": ["kpi", "logs"]})
        result = get_visibility(user)
        assert result["stats"] is False
        assert result["activity"] is False
        assert result["widgets"] == ["kpi", "logs"]

    def test_get_visibility_default_values_are_true(self) -> None:
        from docreview360.dashboard_prefs import get_visibility

        result = get_visibility("testuser_defaults_only_xyz")
        assert result["stats"] is True
        assert result["status"] is True
        assert result["activity"] is True
        assert result["logs"] is True

    def test_set_visibility_widgets_only(self) -> None:
        from docreview360.dashboard_prefs import get_visibility, set_visibility

        user = "testuser_widgets_only_xyz"
        set_visibility(user, {"widgets": ["kpi", "status", "errors"]})
        result = get_visibility(user)
        assert result["widgets"] == ["kpi", "status", "errors"]
        # Legacy boolean keys should still be present with defaults
        assert result["stats"] is True

    def test_set_visibility_booleans_only(self) -> None:
        from docreview360.dashboard_prefs import get_visibility, set_visibility

        user = "testuser_bools_only_xyz"
        set_visibility(user, {"logs": False, "status": False})
        result = get_visibility(user)
        assert result["logs"] is False
        assert result["status"] is False
        assert result["widgets"] == []

    def test_set_visibility_overwrite_widgets(self) -> None:
        from docreview360.dashboard_prefs import get_visibility, set_visibility

        user = "testuser_overwrite_xyz"
        set_visibility(user, {"widgets": ["kpi", "logs"]})
        set_visibility(user, {"widgets": ["status", "activity", "errors"]})
        result = get_visibility(user)
        assert result["widgets"] == ["status", "activity", "errors"]

    def test_set_visibility_empty_widgets_list(self) -> None:
        from docreview360.dashboard_prefs import get_visibility, set_visibility

        user = "testuser_empty_widgets_xyz"
        set_visibility(user, {"widgets": ["kpi"]})
        set_visibility(user, {"widgets": []})
        result = get_visibility(user)
        assert result["widgets"] == []

    def test_visibility_record_in_db(self) -> None:
        """Confirm a DashboardVisibilityRecord row is created in the DB."""
        from docreview360.logs._db import _get_db
        from docreview360.dashboard_prefs import set_visibility
        from docreview360.models import DashboardVisibilityRecord

        user = "testuser_db_check_xyz"
        set_visibility(user, {"widgets": ["kpi", "roles"], "stats": False})
        db = _get_db()
        with db.orm_session() as session:
            record = session.get(DashboardVisibilityRecord, user)
        assert record is not None
        assert record.username == user
        assert "widgets" in record.widgets
        assert record.widgets["widgets"] == ["kpi", "roles"]
        assert record.widgets.get("stats") is False


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestDashboardVisibilityEndpoints:
    """Integration tests for GET/PUT /dashboard/visibility."""

    def test_get_visibility_returns_200_with_defaults(self) -> None:
        client = TestClient(app)
        resp = client.get("/dashboard/visibility", headers=_alice_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert "stats" in body
        assert "widgets" in body

    def test_get_visibility_widgets_field_is_list(self) -> None:
        client = TestClient(app)
        resp = client.get("/dashboard/visibility", headers=_alice_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["widgets"], list)

    def test_put_visibility_with_widgets_list(self) -> None:
        client = TestClient(app)
        payload = {"widgets": ["kpi", "status", "activity"]}
        resp = client.put(
            "/dashboard/visibility",
            json=payload,
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["widgets"] == ["kpi", "status", "activity"]

    def test_put_visibility_with_legacy_booleans(self) -> None:
        client = TestClient(app)
        payload = {"stats": False, "logs": False}
        resp = client.put(
            "/dashboard/visibility",
            json=payload,
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["stats"] is False
        assert body["logs"] is False

    def test_put_visibility_combined_booleans_and_widgets(self) -> None:
        client = TestClient(app)
        payload = {"stats": True, "activity": False, "widgets": ["kpi", "logs", "errors"]}
        resp = client.put(
            "/dashboard/visibility",
            json=payload,
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["stats"] is True
        assert body["activity"] is False
        assert body["widgets"] == ["kpi", "logs", "errors"]

    def test_put_then_get_roundtrip(self) -> None:
        client = TestClient(app)
        headers = _bob_headers()
        widgets_to_save = ["kpi", "reviews", "deadlines"]
        put_resp = client.put(
            "/dashboard/visibility",
            json={"widgets": widgets_to_save},
            headers=headers,
        )
        assert put_resp.status_code == 200

        get_resp = client.get("/dashboard/visibility", headers=headers)
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["widgets"] == widgets_to_save

    def test_get_visibility_requires_auth(self) -> None:
        client = TestClient(app)
        resp = client.get("/dashboard/visibility")
        assert resp.status_code in (401, 403)

    def test_put_visibility_requires_auth(self) -> None:
        client = TestClient(app)
        resp = client.put("/dashboard/visibility", json={"stats": True})
        assert resp.status_code in (401, 403)

    def test_put_visibility_empty_payload_returns_defaults(self) -> None:
        """An empty PUT body should return current defaults without raising."""
        client = TestClient(app)
        resp = client.put(
            "/dashboard/visibility",
            json={},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "stats" in body
        assert "widgets" in body

    def test_put_visibility_null_widgets_not_stored(self) -> None:
        """Omitting widgets key should not clobber existing widget list."""
        client = TestClient(app)
        headers = _alice_headers()
        # First save a widget list
        client.put(
            "/dashboard/visibility",
            json={"widgets": ["kpi", "status"]},
            headers=headers,
        )
        # Then PUT only a boolean — widgets key absent so excluded by model_dump filtering
        resp = client.put(
            "/dashboard/visibility",
            json={"stats": False},
            headers=headers,
        )
        assert resp.status_code == 200
