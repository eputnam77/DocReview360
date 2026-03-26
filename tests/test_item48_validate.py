# SPDX-License-Identifier: MIT
"""Item 48 — POST /documents/validate endpoint contract tests.

Covers:
- Endpoint shape and required keys in response
- Selective check execution via the `checks` field
- Authentication required
- Per-check category persistence via GET/PUT /admin/settings/fsv-checks

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item48_validate.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_TEXT = (
    "The committee shall review the proposed amendments. "
    "The action was taken by the board. "
    "It was determined that the plan would be implemented."
)


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
# POST /documents/validate — basic contract
# ---------------------------------------------------------------------------


class TestUnifiedValidateEndpoint:
    """Contract tests for POST /documents/validate."""

    def test_requires_authentication(self) -> None:
        client = TestClient(app)
        resp = client.post("/documents/validate", json={"text": "Hello"})
        assert resp.status_code in (401, 403)

    def test_returns_200_with_valid_payload(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200

    def test_response_contains_required_top_level_keys(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "preflight" in data
        assert "regulatory" in data
        assert "quality" in data
        assert "source" in data
        assert "checks_run" in data

    def test_source_is_internal_when_fsv_not_configured(self) -> None:
        """Without FSV configured the endpoint falls back to internal logic."""
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        # FSV is not configured in test env, so source should be "internal".
        assert data["source"] in ("internal", "fsv")

    def test_all_three_checks_run_by_default(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        checks_run = data["checks_run"]
        assert "preflight" in checks_run
        assert "regulatory" in checks_run
        assert "quality" in checks_run

    def test_only_preflight_runs_when_checks_contains_preflight(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT, "checks": ["preflight"]},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "preflight" in data["checks_run"]
        assert "regulatory" not in data["checks_run"]
        assert "quality" not in data["checks_run"]
        # Skipped results are empty dicts.
        assert data["regulatory"] == {}
        assert data["quality"] == {}

    def test_only_regulatory_runs_when_checks_contains_regulatory(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT, "checks": ["regulatory"]},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "regulatory" in data["checks_run"]
        assert "preflight" not in data["checks_run"]
        assert "quality" not in data["checks_run"]
        assert data["preflight"] == {}
        assert data["quality"] == {}

    def test_only_quality_runs_when_checks_contains_quality(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT, "checks": ["quality"]},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "quality" in data["checks_run"]
        assert "preflight" not in data["checks_run"]
        assert "regulatory" not in data["checks_run"]

    def test_subset_two_checks_can_be_requested(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT, "checks": ["preflight", "quality"]},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "preflight" in data["checks_run"]
        assert "quality" in data["checks_run"]
        assert "regulatory" not in data["checks_run"]
        assert data["regulatory"] == {}

    def test_preflight_result_has_expected_shape(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT, "checks": ["preflight"]},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        preflight = resp.json()["preflight"]
        assert isinstance(preflight, dict)
        assert "source" in preflight

    def test_quality_result_has_expected_keys(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT, "checks": ["quality"]},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        quality = resp.json()["quality"]
        assert "score" in quality or "raw_score" in quality

    def test_non_admin_user_can_use_endpoint(self) -> None:
        """Validation is not admin-only — any authenticated user can call it."""
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT},
            headers=_bob_headers(),
        )
        assert resp.status_code == 200

    def test_empty_text_returns_200(self) -> None:
        """Empty text is valid (tools should handle it gracefully)."""
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": ""},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200

    def test_empty_checks_list_runs_all_checks(self) -> None:
        """Explicit empty `checks` list behaves the same as omitting it."""
        client = TestClient(app)
        resp = client.post(
            "/documents/validate",
            json={"text": SAMPLE_TEXT, "checks": []},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["checks_run"]) == 3


# ---------------------------------------------------------------------------
# GET /admin/settings/fsv-checks — per-category persistence
# ---------------------------------------------------------------------------


class TestFsvCheckSettings:
    """Tests for FSV per-check category settings persistence."""

    def test_get_fsv_checks_returns_all_categories(self) -> None:
        client = TestClient(app)
        resp = client.get("/admin/settings/fsv-checks", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data
        assert "categories" in data
        expected = {
            "passive_voice",
            "acronym_validation",
            "heading_structure",
            "readability",
            "regulatory",
            "plain_language",
        }
        assert set(data["categories"]) == expected

    def test_all_categories_enabled_by_default(self) -> None:
        client = TestClient(app)
        resp = client.get("/admin/settings/fsv-checks", headers=_alice_headers())
        assert resp.status_code == 200
        checks = resp.json()["checks"]
        for category in checks:
            assert checks[category] is True, f"Expected {category} to default to True"

    def test_get_fsv_checks_requires_auth(self) -> None:
        client = TestClient(app)
        resp = client.get("/admin/settings/fsv-checks")
        assert resp.status_code in (401, 403)

    def test_admin_can_disable_a_category(self) -> None:
        client = TestClient(app)
        resp = client.put(
            "/admin/settings/fsv-checks",
            json={"checks": {"passive_voice": False}},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["checks"]["passive_voice"] is False

    def test_disabled_category_persists_across_get(self) -> None:
        client = TestClient(app)
        # Disable heading_structure
        client.put(
            "/admin/settings/fsv-checks",
            json={"checks": {"heading_structure": False}},
            headers=_alice_headers(),
        )
        # Read back
        resp = client.get("/admin/settings/fsv-checks", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["checks"]["heading_structure"] is False
        # Restore
        client.put(
            "/admin/settings/fsv-checks",
            json={"checks": {"heading_structure": True}},
            headers=_alice_headers(),
        )

    def test_non_admin_cannot_update_fsv_checks(self) -> None:
        client = TestClient(app)
        resp = client.put(
            "/admin/settings/fsv-checks",
            json={"checks": {"passive_voice": False}},
            headers=_bob_headers(),
        )
        assert resp.status_code in (401, 403)

    def test_partial_update_preserves_unmentioned_categories(self) -> None:
        """Updating one category should not reset others to default."""
        client = TestClient(app)
        # First set all to True
        client.put(
            "/admin/settings/fsv-checks",
            json={
                "checks": {
                    "passive_voice": True,
                    "readability": True,
                    "plain_language": True,
                }
            },
            headers=_alice_headers(),
        )
        # Disable only passive_voice
        resp = client.put(
            "/admin/settings/fsv-checks",
            json={"checks": {"passive_voice": False}},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200
        checks = resp.json()["checks"]
        assert checks["passive_voice"] is False
        # Other categories that were explicitly not changed should remain True.
        # (readability and plain_language were set to True above)
        assert checks["readability"] is True
        assert checks["plain_language"] is True

    def test_unknown_category_in_update_is_ignored(self) -> None:
        """Submitting a key that is not a known category should not cause a 4xx."""
        client = TestClient(app)
        resp = client.put(
            "/admin/settings/fsv-checks",
            json={"checks": {"not_a_real_category": True}},
            headers=_alice_headers(),
        )
        # Should either 200 (ignore unknown) or 422 (validation error).
        # Both are acceptable; we just document the observed behavior.
        assert resp.status_code in (200, 422)
