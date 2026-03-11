# SPDX-License-Identifier: MIT
"""Item 46 Phase 3 — Branding/terminology overrides with i18n.

Tests:
- GET /i18n/translations/en  → base translations (no org override)
- GET /i18n/terminology/en   → without org terminology returns same strings as translations
- Setting org terminology project_singular makes nav.projects → custom value
- Terminology override falls back to base translation when no override exists
- GET /i18n/terminology/es   → Spanish base strings with org terminology applied
- Unsupported locale returns 404
- terminology.* keys are exposed in merged translations
- Multiple terminology overrides applied simultaneously
- reset_terminology restores defaults in merged translations

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item46_terminology_merge.py -v
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


# ---------------------------------------------------------------------------
# GET /i18n/translations/en — baseline (no org overrides)
# ---------------------------------------------------------------------------


class TestBaseTranslationsUnchanged:
    def test_base_english_translations_returns_nav_projects(self):
        """Base translations endpoint returns standard nav.projects string."""
        client = TestClient(app)
        resp = client.get("/i18n/translations/en", headers=_alice_headers())
        assert resp.status_code == 200
        strings = resp.json()["strings"]
        assert strings.get("nav.projects") == "Projects"

    def test_base_translations_locale_field_correct(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/en", headers=_alice_headers())
        assert resp.status_code == 200
        assert resp.json()["locale"] == "en"

    def test_base_translations_has_all_expected_keys(self):
        client = TestClient(app)
        resp = client.get("/i18n/translations/en", headers=_alice_headers())
        assert resp.status_code == 200
        strings = resp.json()["strings"]
        for key in ("nav.dashboard", "nav.projects", "nav.documents", "common.save"):
            assert key in strings, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# GET /i18n/terminology/{locale} — without org overrides
# ---------------------------------------------------------------------------


class TestTerminologyEndpointNoOverrides:
    def test_terminology_endpoint_returns_200_for_english(self):
        client = TestClient(app)
        resp = client.get("/i18n/terminology/en", headers=_alice_headers())
        assert resp.status_code == 200

    def test_terminology_response_has_locale_and_strings(self):
        client = TestClient(app)
        resp = client.get("/i18n/terminology/en", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "locale" in data
        assert "strings" in data
        assert data["locale"] == "en"

    def test_terminology_without_overrides_matches_base_nav_projects(self):
        """Without org terminology, nav.projects should equal the default English string."""
        client = TestClient(app)
        resp = client.get("/i18n/terminology/en?org_id=nonexistent-org-xyz", headers=_alice_headers())
        assert resp.status_code == 200
        strings = resp.json()["strings"]
        assert strings.get("nav.projects") == "Projects"

    def test_terminology_unsupported_locale_returns_404(self):
        client = TestClient(app)
        resp = client.get("/i18n/terminology/zh", headers=_alice_headers())
        assert resp.status_code == 404

    def test_terminology_requires_auth(self):
        client = TestClient(app)
        resp = client.get("/i18n/terminology/en")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /i18n/terminology/{locale} — WITH org terminology overrides
# ---------------------------------------------------------------------------


class TestTerminologyMergeWithOverrides:
    """These tests set org terminology and verify merged translations reflect the override."""

    def _set_terminology(self, org_id: str, **kwargs: str) -> None:
        from docreview360.db_store import get_db
        from docreview360.branding import set_terminology

        with get_db().orm_session() as db:
            set_terminology(db, org_id, updated_by="alice", **kwargs)

    def _reset_terminology(self, org_id: str) -> None:
        from docreview360.db_store import get_db
        from docreview360.branding import reset_terminology

        with get_db().orm_session() as db:
            reset_terminology(db, org_id, updated_by="alice")

    def test_projects_override_reflected_in_nav_projects(self):
        """Setting terminology.projects='Cases' must change nav.projects in merged response."""
        org_id = "test-org-term-cases"
        self._set_terminology(org_id, projects="Cases")
        try:
            client = TestClient(app)
            resp = client.get(
                f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
            )
            assert resp.status_code == 200
            strings = resp.json()["strings"]
            assert strings.get("nav.projects") == "Cases", (
                f"Expected 'Cases' but got {strings.get('nav.projects')!r}"
            )
        finally:
            self._reset_terminology(org_id)

    def test_documents_override_reflected_in_nav_documents(self):
        """Setting terminology.documents='Records' must change nav.documents in merged response."""
        org_id = "test-org-term-records"
        self._set_terminology(org_id, documents="Records")
        try:
            client = TestClient(app)
            resp = client.get(
                f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
            )
            assert resp.status_code == 200
            strings = resp.json()["strings"]
            assert strings.get("nav.documents") == "Records"
        finally:
            self._reset_terminology(org_id)

    def test_terminology_fallback_when_no_override_for_key(self):
        """Keys not overridden by terminology should retain the base translation."""
        org_id = "test-org-term-partial"
        # Only override 'projects'; 'common.save' and 'nav.dashboard' should be unchanged.
        self._set_terminology(org_id, projects="Cases")
        try:
            client = TestClient(app)
            resp = client.get(
                f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
            )
            assert resp.status_code == 200
            strings = resp.json()["strings"]
            # Overridden key
            assert strings.get("nav.projects") == "Cases"
            # Non-overridden keys should remain unchanged
            assert strings.get("common.save") == "Save"
            assert strings.get("nav.dashboard") == "Dashboard"
        finally:
            self._reset_terminology(org_id)

    def test_spanish_base_with_org_terminology_override(self):
        """Org terminology override is applied on top of Spanish base strings."""
        org_id = "test-org-term-es"
        self._set_terminology(org_id, projects="Casos")
        try:
            client = TestClient(app)
            resp = client.get(
                f"/i18n/terminology/es?org_id={org_id}", headers=_alice_headers()
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["locale"] == "es"
            strings = data["strings"]
            # org override wins over the Spanish translation for nav.projects
            assert strings.get("nav.projects") == "Casos"
            # non-overridden Spanish strings are preserved
            assert strings.get("common.save") == "Guardar"
        finally:
            self._reset_terminology(org_id)

    def test_terminology_values_exposed_under_terminology_namespace(self):
        """Merged translations must include terminology.* keys directly."""
        org_id = "test-org-term-ns"
        self._set_terminology(org_id, projects="Cases", reviewer="Approver")
        try:
            client = TestClient(app)
            resp = client.get(
                f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
            )
            assert resp.status_code == 200
            strings = resp.json()["strings"]
            assert strings.get("terminology.projects") == "Cases"
            assert strings.get("terminology.reviewer") == "Approver"
        finally:
            self._reset_terminology(org_id)

    def test_multiple_overrides_applied_simultaneously(self):
        """Multiple terminology overrides are all reflected in one request."""
        org_id = "test-org-term-multi"
        self._set_terminology(org_id, projects="Cases", documents="Records")
        try:
            client = TestClient(app)
            resp = client.get(
                f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
            )
            assert resp.status_code == 200
            strings = resp.json()["strings"]
            assert strings.get("nav.projects") == "Cases"
            assert strings.get("nav.documents") == "Records"
        finally:
            self._reset_terminology(org_id)

    def test_reset_terminology_restores_defaults(self):
        """After reset_terminology, merged translations should return to defaults."""
        org_id = "test-org-term-reset"
        self._set_terminology(org_id, projects="Cases")
        # Verify override is active
        client = TestClient(app)
        resp = client.get(
            f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
        )
        assert resp.json()["strings"].get("nav.projects") == "Cases"

        # Reset and verify default is restored
        self._reset_terminology(org_id)
        resp2 = client.get(
            f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
        )
        assert resp2.status_code == 200
        assert resp2.json()["strings"].get("nav.projects") == "Projects"

    def test_org_id_returned_in_response(self):
        """The org_id query param should be echoed back in the response body."""
        org_id = "test-org-term-echo"
        client = TestClient(app)
        resp = client.get(
            f"/i18n/terminology/en?org_id={org_id}", headers=_alice_headers()
        )
        assert resp.status_code == 200
        assert resp.json().get("org_id") == org_id
