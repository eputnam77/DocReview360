# SPDX-License-Identifier: MIT
"""Tests for Item 40 Phase 3: i18n framework and branding/white-label support."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# i18n unit tests
# ---------------------------------------------------------------------------


class TestI18n:
    def test_translate_english_default(self):
        from docreview360.i18n import translate

        assert translate("common.save") == "Save"

    def test_translate_spanish(self):
        from docreview360.i18n import translate

        assert translate("common.save", "es") == "Guardar"

    def test_translate_french(self):
        from docreview360.i18n import translate

        assert translate("nav.dashboard", "fr") == "Tableau de bord"

    def test_translate_german(self):
        from docreview360.i18n import translate

        assert translate("nav.projects", "de") == "Projekte"

    def test_translate_unknown_key_returns_key(self):
        from docreview360.i18n import translate

        assert translate("nonexistent.key", "en") == "nonexistent.key"

    def test_translate_unsupported_locale_falls_back_to_english(self):
        from docreview360.i18n import translate

        assert translate("common.save", "zh") == "Save"

    def test_translate_with_kwargs(self):
        from docreview360.i18n import _TRANSLATIONS, translate

        # Temporarily add a template string
        _TRANSLATIONS["test.greeting"] = {"en": "Hello, {name}!"}
        result = translate("test.greeting", "en", name="Alice")
        assert result == "Hello, Alice!"
        del _TRANSLATIONS["test.greeting"]

    def test_detect_locale_simple(self):
        from docreview360.i18n import detect_locale

        assert detect_locale("fr") == "fr"
        assert detect_locale("es-MX") == "es"
        assert detect_locale("de-DE") == "de"

    def test_detect_locale_with_quality(self):
        from docreview360.i18n import detect_locale

        # "fr-CH, fr;q=0.9, en;q=0.8, de;q=0.7"
        assert detect_locale("fr-CH, fr;q=0.9, en;q=0.8") == "fr"

    def test_detect_locale_fallback_to_english(self):
        from docreview360.i18n import detect_locale

        assert detect_locale("zh-CN, zh;q=0.9") == "en"
        assert detect_locale(None) == "en"
        assert detect_locale("") == "en"

    def test_list_locales(self):
        from docreview360.i18n import list_locales

        locales = list_locales()
        codes = [loc["code"] for loc in locales]
        assert "en" in codes
        assert "es" in codes
        assert "fr" in codes
        assert "de" in codes
        # English should be default
        defaults = [loc for loc in locales if loc["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["code"] == "en"

    def test_get_namespace(self):
        from docreview360.i18n import get_namespace

        nav_en = get_namespace("nav", "en")
        assert "dashboard" in nav_en
        assert nav_en["dashboard"] == "Dashboard"

        nav_es = get_namespace("nav", "es")
        assert nav_es["dashboard"] == "Panel"

    def test_format_date(self):
        from datetime import datetime

        from docreview360.i18n import format_date

        dt = datetime(2026, 3, 15)
        assert format_date(dt, "en") == "03/15/2026"
        assert format_date(dt, "fr") == "15/03/2026"
        assert format_date(dt, "de") == "15.03.2026"
        assert format_date(None) == ""


# ---------------------------------------------------------------------------
# Branding unit tests
# ---------------------------------------------------------------------------


class TestBranding:
    def _setup_org(self, db, suffix=""):
        """No DB setup needed — branding uses OrgConfig under the hood."""
        return f"test-org-brand-{suffix}"

    def test_default_branding(self):
        from docreview360.branding import BRANDING_DEFAULTS, get_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "default")
            result = get_branding(db, org_id)
            assert result["company_name"] == BRANDING_DEFAULTS["company_name"]
            assert result["primary_color"] == BRANDING_DEFAULTS["primary_color"]

    def test_set_branding_company_name(self):
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "company")
            set_branding(db, org_id, updated_by="alice", company_name="Acme Corp")
            result = get_branding(db, org_id)
            assert result["company_name"] == "Acme Corp"

    def test_set_branding_colors(self):
        from docreview360.branding import get_branding, set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "colors")
            set_branding(db, org_id, updated_by="alice", primary_color="#ff5500", accent_color="#003366")
            result = get_branding(db, org_id)
            assert result["primary_color"] == "#ff5500"
            assert result["accent_color"] == "#003366"

    def test_invalid_color_raises(self):
        from docreview360.branding import set_branding
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "bad-color")
            with pytest.raises(ValueError, match="hex"):
                set_branding(db, org_id, updated_by="alice", primary_color="red")

    def test_set_and_reset_branding(self):
        from docreview360.branding import (
            BRANDING_DEFAULTS,
            get_branding,
            reset_branding,
            set_branding,
        )
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "reset")
            set_branding(db, org_id, updated_by="alice", company_name="Custom Name")
            assert get_branding(db, org_id)["company_name"] == "Custom Name"
            reset_branding(db, org_id, updated_by="alice")
            assert get_branding(db, org_id)["company_name"] == BRANDING_DEFAULTS["company_name"]

    def test_terminology_defaults(self):
        from docreview360.branding import TERMINOLOGY_DEFAULTS, get_terminology
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "terms-default")
            result = get_terminology(db, org_id)
            assert result["project"] == TERMINOLOGY_DEFAULTS["project"]
            assert result["document"] == TERMINOLOGY_DEFAULTS["document"]

    def test_set_terminology(self):
        from docreview360.branding import get_terminology, set_terminology
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "terms-set")
            set_terminology(db, org_id, updated_by="alice", project="Case", projects="Cases")
            result = get_terminology(db, org_id)
            assert result["project"] == "Case"
            assert result["projects"] == "Cases"

    def test_get_full_theme(self):
        from docreview360.branding import get_full_theme
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            org_id = self._setup_org(db, "theme")
            theme = get_full_theme(db, org_id)
            assert "org_id" in theme
            assert "branding" in theme
            assert "terminology" in theme


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestBrandingAPI:
    def _alice_headers(self, client):
        from docreview360 import auth, rbac

        try:
            auth.create_user("alice", "password")
        except Exception:
            pass
        rbac.add_role("alice", "admin")
        resp = client.post("/token", data={"username": "alice", "password": "password"})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_org_branding_endpoint(self):
        from docreview360.api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/orgs/test-org-api/branding", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "branding" in data
        assert "terminology" in data

    def test_set_org_branding_endpoint(self):
        from docreview360.api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.put(
            "/orgs/test-org-api/branding",
            json={"company_name": "Test Corp"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["branding"]["company_name"] == "Test Corp"

    def test_list_locales_endpoint(self):
        from docreview360.api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/i18n/locales", headers=headers)
        assert resp.status_code == 200
        codes = [loc["code"] for loc in resp.json()]
        assert "en" in codes
        assert "fr" in codes

    def test_get_translations_endpoint(self):
        from docreview360.api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/i18n/translations/fr?namespace=nav", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["locale"] == "fr"
        assert data["strings"]["dashboard"] == "Tableau de bord"

    def test_get_translations_unsupported_locale(self):
        from docreview360.api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        headers = self._alice_headers(client)
        resp = client.get("/i18n/translations/zh", headers=headers)
        assert resp.status_code == 404
