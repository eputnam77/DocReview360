# SPDX-License-Identifier: MIT
"""Item 46 Phase 1 — Frontend localization hook, switcher, and backend locale preference.

Tests:
- GET /i18n/locales  → includes en, es, fr, de
- GET /i18n/translations/en  → nested dict with expected keys
- GET /i18n/translations/es  → Spanish strings
- GET /i18n/translations/xx  → 404 for unsupported locale
- PUT /users/me/locale  → saves and returns updated locale
- GET /users/me/locale  → returns current locale
- PUT /users/me/locale with invalid locale → 400
- profile.update_preferences handles locale key
- profile.get_preferences returns saved locale

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item46_i18n.py -v
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
# GET /i18n/locales
# ---------------------------------------------------------------------------


class TestListLocalesEndpoint:
    def test_locales_includes_all_supported(self):
        client = TestClient(app)
        resp = client.get("/i18n/locales", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        codes = [item["code"] for item in data]
        assert "en" in codes
        assert "es" in codes
        assert "fr" in codes
        assert "de" in codes

    def test_locales_has_name_and_is_default_fields(self):
        client = TestClient(app)
        resp = client.get("/i18n/locales", headers=_alice_headers())
        assert resp.status_code == 200
        for item in resp.json():
            assert "code" in item
            assert "name" in item
            assert "is_default" in item

    def test_locales_english_is_default(self):
        client = TestClient(app)
        resp = client.get("/i18n/locales", headers=_alice_headers())
        assert resp.status_code == 200
        defaults = [item for item in resp.json() if item["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["code"] == "en"

    def test_locales_requires_auth(self):
        client = TestClient(app)
        resp = client.get("/i18n/locales")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /i18n/translations/{locale}
# ---------------------------------------------------------------------------


class TestGetTranslationsEndpoint:
    def test_english_translations_returns_strings(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/en", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["locale"] == "en"
        assert isinstance(data["strings"], dict)
        assert len(data["strings"]) > 0

    def test_english_translations_contains_nav_dashboard(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/en", headers=_alice_headers())
        assert resp.status_code == 200
        strings = resp.json()["strings"]
        assert "nav.dashboard" in strings
        assert strings["nav.dashboard"] == "Dashboard"

    def test_english_translations_contains_common_save(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/en", headers=_alice_headers())
        assert resp.status_code == 200
        strings = resp.json()["strings"]
        assert "common.save" in strings
        assert strings["common.save"] == "Save"

    def test_spanish_translations_returns_correct_strings(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/es", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["locale"] == "es"
        strings = data["strings"]
        assert strings.get("nav.dashboard") == "Panel"
        assert strings.get("common.save") == "Guardar"
        assert strings.get("common.cancel") == "Cancelar"

    def test_french_translations_returns_correct_strings(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/fr", headers=_alice_headers())
        assert resp.status_code == 200
        strings = resp.json()["strings"]
        assert strings.get("nav.dashboard") == "Tableau de bord"
        assert strings.get("common.save") == "Enregistrer"

    def test_german_translations_returns_correct_strings(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/de", headers=_alice_headers())
        assert resp.status_code == 200
        strings = resp.json()["strings"]
        assert strings.get("nav.projects") == "Projekte"
        assert strings.get("common.delete") == "Löschen"

    def test_unsupported_locale_returns_404(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/zh", headers=_alice_headers())
        assert resp.status_code == 404

    def test_translations_requires_auth(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/en")
        assert resp.status_code == 401

    def test_translations_namespace_filter(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/en?namespace=nav", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["namespace"] == "nav"
        assert "dashboard" in data["strings"]
        assert "Projects" not in data["strings"]  # should only be nav keys

    def test_translations_all_locales_have_doc_status_keys(self):
        client = TestClient(app)
        for locale in ("en", "es", "fr", "de"):
            resp = client.get(f"/i18n/translations/{locale}", headers=_alice_headers())
            assert resp.status_code == 200
            strings = resp.json()["strings"]
            assert "doc.status.draft" in strings, f"Missing doc.status.draft for {locale}"
            assert "doc.status.approved" in strings, f"Missing doc.status.approved for {locale}"


# ---------------------------------------------------------------------------
# GET /users/me/locale and PUT /users/me/locale
# ---------------------------------------------------------------------------


class TestUserLocaleEndpoints:
    def test_get_locale_returns_default_en(self):
        """Fresh user should default to 'en'."""
        client = TestClient(app)
        # Create a fresh user to avoid state from other tests
        try:
            auth.USER_REPOSITORY.create_user("locale_test_user", "TestPass123!")
        except Exception:
            pass
        token = auth.create_access_token({"sub": "locale_test_user"}, timedelta(minutes=30))
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/users/me/locale", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "locale" in data
        assert data["locale"] == "en"

    def test_put_locale_saves_and_returns_locale(self):
        client = TestClient(app)
        resp = client.put(
            "/users/me/locale",
            json={"locale": "es"},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["locale"] == "es"

    def test_put_locale_then_get_returns_updated_locale(self):
        client = TestClient(app)
        headers = _bob_headers()
        # Set locale to French
        put_resp = client.put(
            "/users/me/locale",
            json={"locale": "fr"},
            headers=headers,
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["locale"] == "fr"
        # Verify get returns the saved value
        get_resp = client.get("/users/me/locale", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["locale"] == "fr"

    def test_put_locale_german(self):
        client = TestClient(app)
        resp = client.put(
            "/users/me/locale",
            json={"locale": "de"},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["locale"] == "de"

    def test_put_locale_invalid_returns_400(self):
        client = TestClient(app)
        resp = client.put(
            "/users/me/locale",
            json={"locale": "zh"},
            headers=_alice_headers(),
        )
        assert resp.status_code == 400

    def test_put_locale_empty_string_returns_400(self):
        client = TestClient(app)
        resp = client.put(
            "/users/me/locale",
            json={"locale": ""},
            headers=_alice_headers(),
        )
        assert resp.status_code == 400

    def test_put_locale_requires_auth(self):
        client = TestClient(app)
        resp = client.put("/users/me/locale", json={"locale": "es"})
        assert resp.status_code == 401

    def test_get_locale_requires_auth(self):
        client = TestClient(app)
        resp = client.get("/users/me/locale")
        assert resp.status_code == 401

    def test_put_locale_normalises_case(self):
        """Locale codes should be normalised to lowercase."""
        client = TestClient(app)
        resp = client.put(
            "/users/me/locale",
            json={"locale": "EN"},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["locale"] == "en"


# ---------------------------------------------------------------------------
# profile.py unit tests for locale preference
# ---------------------------------------------------------------------------


class TestProfileLocalePreference:
    def test_update_preferences_saves_valid_locale(self):
        from docreview360.profile import update_preferences, get_preferences

        update_preferences("test_profile_locale", {"locale": "es"})
        prefs = get_preferences("test_profile_locale")
        assert prefs.get("locale") == "es"

    def test_update_preferences_rejects_invalid_locale(self):
        from docreview360.profile import update_preferences, get_preferences

        # Invalid locale should be silently ignored (not saved)
        update_preferences("test_profile_locale2", {"locale": "xx"})
        prefs = get_preferences("test_profile_locale2")
        assert prefs.get("locale") != "xx"

    def test_update_preferences_saves_all_supported_locales(self):
        from docreview360.profile import update_preferences, get_preferences

        for locale in ("en", "es", "fr", "de"):
            update_preferences(f"locale_user_{locale}", {"locale": locale})
            prefs = get_preferences(f"locale_user_{locale}")
            assert prefs.get("locale") == locale, f"Failed to save locale {locale}"

    def test_update_preferences_locale_does_not_affect_theme(self):
        from docreview360.profile import update_preferences, get_preferences

        update_preferences("locale_theme_user", {"theme": "dark", "locale": "fr"})
        prefs = get_preferences("locale_theme_user")
        assert prefs.get("locale") == "fr"
        assert prefs.get("theme") == "dark"

    def test_valid_locales_set_contains_expected_values(self):
        from docreview360.profile import VALID_LOCALES

        assert "en" in VALID_LOCALES
        assert "es" in VALID_LOCALES
        assert "fr" in VALID_LOCALES
        assert "de" in VALID_LOCALES
