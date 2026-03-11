# SPDX-License-Identifier: MIT
"""Tests for Item 42: theme and white-label color support.

Covers:
- get_branding() defaults for new color fields (sidebar_bg, sidebar_text)
- set_branding() stores primary_color, accent_color, sidebar_bg, sidebar_text
- Hex color validation (rejects invalid values, accepts 3- and 6-char hex)
- GET /branding returns color fields in the public API response
- GET /orgs/{id}/branding returns color fields
- PUT /orgs/{id}/branding persists color fields
- Reset clears color fields back to defaults
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# Unit tests — branding.py
# ---------------------------------------------------------------------------


class TestBrandingColorDefaults:
    """get_branding() returns sensible defaults for all four new color fields."""

    def _unique_org(self, suffix: str) -> str:
        return f"theming-test-org-{suffix}"

    def test_sidebar_bg_default_is_none(self):
        from docreview360.branding import BRANDING_DEFAULTS, get_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            result = get_branding(db, self._unique_org("sidebar-bg-default"))
        assert result["sidebar_bg"] == BRANDING_DEFAULTS["sidebar_bg"]

    def test_sidebar_text_default_is_none(self):
        from docreview360.branding import BRANDING_DEFAULTS, get_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            result = get_branding(db, self._unique_org("sidebar-text-default"))
        assert result["sidebar_text"] == BRANDING_DEFAULTS["sidebar_text"]

    def test_primary_color_has_default(self):
        from docreview360.branding import BRANDING_DEFAULTS, get_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            result = get_branding(db, self._unique_org("primary-default"))
        assert result["primary_color"] == BRANDING_DEFAULTS["primary_color"]
        assert result["primary_color"] is not None

    def test_accent_color_has_default(self):
        from docreview360.branding import BRANDING_DEFAULTS, get_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            result = get_branding(db, self._unique_org("accent-default"))
        assert result["accent_color"] == BRANDING_DEFAULTS["accent_color"]
        assert result["accent_color"] is not None

    def test_all_four_color_keys_present_in_defaults(self):
        """BRANDING_DEFAULTS must declare all four color keys."""
        from docreview360.branding import BRANDING_DEFAULTS

        for key in ("primary_color", "accent_color", "sidebar_bg", "sidebar_text"):
            assert key in BRANDING_DEFAULTS, f"Missing key: {key}"


class TestBrandingColorStorage:
    """set_branding() stores and retrieves each of the four theme color fields."""

    def _unique_org(self, suffix: str) -> str:
        return f"theming-store-org-{suffix}"

    def test_set_primary_color(self):
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org = self._unique_org("primary")
            set_branding(db, org, updated_by="admin", primary_color="#6366f1")
            result = get_branding(db, org)
        assert result["primary_color"] == "#6366f1"

    def test_set_accent_color(self):
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org = self._unique_org("accent")
            set_branding(db, org, updated_by="admin", accent_color="#22d3ee")
            result = get_branding(db, org)
        assert result["accent_color"] == "#22d3ee"

    def test_set_sidebar_bg(self):
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org = self._unique_org("sidebar-bg")
            set_branding(db, org, updated_by="admin", sidebar_bg="#1e293b")
            result = get_branding(db, org)
        assert result["sidebar_bg"] == "#1e293b"

    def test_set_sidebar_text(self):
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org = self._unique_org("sidebar-text")
            set_branding(db, org, updated_by="admin", sidebar_text="#f8fafc")
            result = get_branding(db, org)
        assert result["sidebar_text"] == "#f8fafc"

    def test_set_all_four_colors_together(self):
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org = self._unique_org("all-four")
            set_branding(
                db,
                org,
                updated_by="admin",
                primary_color="#6366f1",
                accent_color="#22d3ee",
                sidebar_bg="#1e293b",
                sidebar_text="#f8fafc",
            )
            result = get_branding(db, org)
        assert result["primary_color"] == "#6366f1"
        assert result["accent_color"] == "#22d3ee"
        assert result["sidebar_bg"] == "#1e293b"
        assert result["sidebar_text"] == "#f8fafc"

    def test_three_char_hex_accepted(self):
        """3-character shorthand hex codes (#RGB) must be accepted."""
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org = self._unique_org("three-char")
            set_branding(db, org, updated_by="admin", primary_color="#abc")
            result = get_branding(db, org)
        assert result["primary_color"] == "#abc"

    def test_reset_clears_color_overrides(self):
        """reset_branding() restores defaults for sidebar_bg and sidebar_text."""
        from docreview360.branding import (
            BRANDING_DEFAULTS,
            get_branding,
            reset_branding,
            set_branding,
        )
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org = self._unique_org("reset")
            set_branding(db, org, updated_by="admin", sidebar_bg="#000000", sidebar_text="#ffffff")
            assert get_branding(db, org)["sidebar_bg"] == "#000000"
            reset_branding(db, org, updated_by="admin")
            after = get_branding(db, org)
        assert after["sidebar_bg"] == BRANDING_DEFAULTS["sidebar_bg"]
        assert after["sidebar_text"] == BRANDING_DEFAULTS["sidebar_text"]


class TestHexColorValidation:
    """_validate_branding_payload() rejects non-hex color strings."""

    def _org(self, suffix: str) -> str:
        return f"theming-valid-org-{suffix}"

    def _call(self, **kwargs):
        from docreview360.db_store import get_db
        from docreview360.branding import set_branding

        with get_db().orm_session() as db:
            return set_branding(db, self._org("v"), updated_by="admin", **kwargs)

    def test_invalid_primary_color_named_color(self):
        with pytest.raises(ValueError, match="hex"):
            self._call(primary_color="red")

    def test_invalid_primary_color_gggggg(self):
        with pytest.raises(ValueError):
            self._call(primary_color="#gggggg")

    def test_invalid_accent_color_no_hash(self):
        with pytest.raises(ValueError, match="hex"):
            self._call(accent_color="6366f1")

    def test_invalid_sidebar_bg_empty(self):
        with pytest.raises(ValueError):
            self._call(sidebar_bg="")

    def test_invalid_sidebar_text_rgb_function(self):
        with pytest.raises(ValueError, match="hex"):
            self._call(sidebar_text="rgb(0, 0, 0)")

    def test_invalid_seven_char_hex(self):
        with pytest.raises(ValueError):
            self._call(primary_color="#1234567")

    def test_none_sidebar_bg_is_accepted(self):
        """None is valid — it means 'use the default (no override)'."""
        from docreview360.db_store import get_db
        from docreview360.branding import set_branding

        with get_db().orm_session() as db:
            org = self._org("none-ok")
            result = set_branding(db, org, updated_by="admin", sidebar_bg=None)
        # sidebar_bg should still be None (not an error)
        assert result["sidebar_bg"] is None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestThemingAPI:
    """HTTP-level tests for branding color fields via FastAPI TestClient."""

    def _alice_headers(self, client):
        from docreview360 import auth, rbac

        try:
            auth.USER_REPOSITORY.create_user(
                "alice",
                auth.DEMO_USER_DEFAULTS["alice"]["password"],
                otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
            )
        except Exception:
            pass
        rbac.add_role("alice", "admin")
        resp = client.post(
            "/token",
            data={"username": "alice", "password": auth.DEMO_USER_DEFAULTS["alice"]["password"]},
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_public_branding_endpoint_has_color_fields(self):
        """GET /branding must include branding_primary_color and related fields."""
        from fastapi.testclient import TestClient

        from docreview360.api import app

        client = TestClient(app)
        resp = client.get("/branding")
        assert resp.status_code == 200
        data = resp.json()
        # Fields exist in the response (even if null)
        assert "branding_primary_color" in data
        assert "branding_accent_color" in data
        assert "branding_sidebar_bg" in data
        assert "branding_sidebar_text" in data

    def test_put_org_branding_with_color_fields(self):
        """PUT /orgs/{id}/branding persists all four color fields."""
        from fastapi.testclient import TestClient

        from docreview360.api import app

        client = TestClient(app)
        headers = self._alice_headers(client)
        payload = {
            "primary_color": "#6366f1",
            "accent_color": "#22d3ee",
            "sidebar_bg": "#1e293b",
            "sidebar_text": "#f8fafc",
        }
        resp = client.put("/orgs/theming-api-org/branding", json=payload, headers=headers)
        assert resp.status_code == 200
        branding = resp.json()["branding"]
        assert branding["primary_color"] == "#6366f1"
        assert branding["accent_color"] == "#22d3ee"
        assert branding["sidebar_bg"] == "#1e293b"
        assert branding["sidebar_text"] == "#f8fafc"

    def test_put_org_branding_invalid_color_returns_422(self):
        """PUT /orgs/{id}/branding with an invalid hex color returns 422."""
        from fastapi.testclient import TestClient

        from docreview360.api import app

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.put(
            "/orgs/theming-api-bad/branding",
            json={"primary_color": "#gggggg"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_get_org_branding_returns_color_fields(self):
        """GET /orgs/{id}/branding returns all four color fields in branding dict."""
        from fastapi.testclient import TestClient

        from docreview360.api import app

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/orgs/theming-get-org/branding", headers=headers)
        assert resp.status_code == 200
        branding = resp.json()["branding"]
        for key in ("primary_color", "accent_color", "sidebar_bg", "sidebar_text"):
            assert key in branding, f"Missing key in branding response: {key}"

    def test_put_then_get_org_branding_roundtrip(self):
        """Values written via PUT are returned unchanged by GET."""
        from fastapi.testclient import TestClient

        from docreview360.api import app

        client = TestClient(app)
        headers = self._alice_headers(client)
        org = "theming-roundtrip-org"
        client.put(
            f"/orgs/{org}/branding",
            json={"sidebar_bg": "#334155", "sidebar_text": "#e2e8f0"},
            headers=headers,
        )
        resp = client.get(f"/orgs/{org}/branding", headers=headers)
        assert resp.status_code == 200
        branding = resp.json()["branding"]
        assert branding["sidebar_bg"] == "#334155"
        assert branding["sidebar_text"] == "#e2e8f0"

    def test_delete_org_branding_resets_color_fields(self):
        """DELETE /orgs/{id}/branding reverts colors to BRANDING_DEFAULTS values."""
        from fastapi.testclient import TestClient

        from docreview360.api import app
        from docreview360.branding import BRANDING_DEFAULTS

        client = TestClient(app)
        headers = self._alice_headers(client)
        org = "theming-reset-api-org"
        client.put(
            f"/orgs/{org}/branding",
            json={"sidebar_bg": "#000000"},
            headers=headers,
        )
        resp = client.delete(f"/orgs/{org}/branding", headers=headers)
        assert resp.status_code == 200
        branding = resp.json()["branding"]
        assert branding["sidebar_bg"] == BRANDING_DEFAULTS["sidebar_bg"]
