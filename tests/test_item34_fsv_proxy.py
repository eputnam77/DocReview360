# SPDX-License-Identifier: MIT
"""Item 34 Phase 1 — FSV proxy layer tests.

Tests cover:
- is_fsv_configured() returns False when env var not set
- is_fsv_configured() returns True when env var set
- GET /fsv/status returns {"configured": false} when not configured
- GET /fsv/status returns {"configured": true, "reachable": false} when configured
  but FSV is unreachable
- POST /documents/preflight response always includes a "source" field
- POST /documents/preflight uses "internal" source when FSV is not configured
- POST /documents/preflight uses "fsv" source when FSV is configured and reachable
- POST /ai/regulatory-check falls back to internal when FSV not configured
- POST /ai/regulatory-check proxies to FSV when configured and returns FSV result

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item34_fsv_proxy.py -v
"""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

client = TestClient(app)


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
# Unit tests: is_fsv_configured()
# ---------------------------------------------------------------------------


class TestIsFsvConfigured:
    """Unit tests for the fsv_proxy.is_fsv_configured() helper."""

    def test_returns_false_when_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_fsv_configured() must return False when FEDERAL_STYLE_VALIDATOR_URL is absent."""
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        # Re-import to pick up cleared env
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        assert _mod.is_fsv_configured() is False

    def test_returns_false_when_env_var_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_fsv_configured() must return False when FEDERAL_STYLE_VALIDATOR_URL is empty."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "")
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        assert _mod.is_fsv_configured() is False

    def test_returns_true_when_env_var_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_fsv_configured() must return True when FEDERAL_STYLE_VALIDATOR_URL is non-empty."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv-service:8080")
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        assert _mod.is_fsv_configured() is True

    def test_get_fsv_url_returns_none_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_fsv_url() must return None when the env var is absent."""
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        assert _mod.get_fsv_url() is None

    def test_get_fsv_url_returns_url_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_fsv_url() must return the configured URL."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv-service:8080")
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        assert _mod.get_fsv_url() == "http://fsv-service:8080"


# ---------------------------------------------------------------------------
# Unit tests: fsv_proxy functions raise NotImplementedError when not configured
# ---------------------------------------------------------------------------


class TestFsvProxyFunctionsUnconfigured:
    """fsv_validate/quality/regulatory_check must raise NotImplementedError when not configured."""

    @pytest.mark.asyncio
    async def test_fsv_validate_raises_when_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        with pytest.raises(NotImplementedError):
            await _mod.fsv_validate("some text")

    @pytest.mark.asyncio
    async def test_fsv_quality_raises_when_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        with pytest.raises(NotImplementedError):
            await _mod.fsv_quality("some text")

    @pytest.mark.asyncio
    async def test_fsv_regulatory_check_raises_when_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        import importlib

        import docreview360.fsv_proxy as _mod
        importlib.reload(_mod)
        with pytest.raises(NotImplementedError):
            await _mod.fsv_regulatory_check("some text")


# ---------------------------------------------------------------------------
# API tests: GET /fsv/status
# ---------------------------------------------------------------------------


class TestFsvStatusEndpoint:
    """Tests for GET /fsv/status."""

    def test_status_not_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns configured=false when FEDERAL_STYLE_VALIDATOR_URL is not set."""
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        headers = _alice_headers()
        resp = client.get("/fsv/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False
        assert data["url"] is None
        assert data["reachable"] is False

    def test_status_configured_but_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns configured=true, reachable=false when FSV is set but not running."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://localhost:19999")
        headers = _alice_headers()
        resp = client.get("/fsv/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["url"] == "http://localhost:19999"
        assert data["reachable"] is False

    def test_status_requires_authentication(self) -> None:
        """GET /fsv/status must reject unauthenticated requests."""
        resp = client.get("/fsv/status")
        assert resp.status_code in (401, 403)

    def test_status_configured_and_reachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns reachable=true when FSV health endpoint responds with 2xx."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv-mock:8080")

        mock_response = MagicMock()
        mock_response.is_success = True

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("docreview360.api.tools_router.httpx.AsyncClient", return_value=mock_client):
            headers = _alice_headers()
            resp = client.get("/fsv/status", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["reachable"] is True


# ---------------------------------------------------------------------------
# API tests: POST /documents/preflight
# ---------------------------------------------------------------------------


class TestPreflightEndpointSource:
    """Tests that POST /documents/preflight always returns a 'source' field."""

    def test_preflight_includes_source_field_internal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FSV is not configured, preflight response includes source='internal'."""
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        headers = _alice_headers()
        resp = client.post(
            "/documents/preflight",
            json={"text": "This is a sample document for testing purposes."},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "source" in data
        assert data["source"] == "internal"

    def test_preflight_source_is_fsv_when_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FSV is configured and reachable, preflight response includes source='fsv'."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv-mock:8080")

        fsv_payload: dict[str, Any] = {
            "passed": True,
            "issues": [],
            "score": 0.95,
        }

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=fsv_payload)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "docreview360.fsv_proxy.httpx.AsyncClient", return_value=mock_client
        ):
            headers = _alice_headers()
            resp = client.post(
                "/documents/preflight",
                json={"text": "Document text forwarded to FSV."},
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "fsv"

    def test_preflight_falls_back_to_internal_on_fsv_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FSV is configured but throws an error, fallback to internal implementation."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv-mock:8080")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

        with patch(
            "docreview360.fsv_proxy.httpx.AsyncClient", return_value=mock_client
        ):
            headers = _alice_headers()
            resp = client.post(
                "/documents/preflight",
                json={"text": "Document text for fallback test."},
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        # Fallback to internal on error
        assert data["source"] == "internal"


# ---------------------------------------------------------------------------
# API tests: POST /ai/regulatory-check
# ---------------------------------------------------------------------------


class TestRegulatoryCheckEndpointFsv:
    """Tests for FSV proxy layer on POST /ai/regulatory-check."""

    def test_regulatory_check_internal_when_fsv_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FSV is not configured, regulatory check uses internal implementation."""
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        headers = _alice_headers()
        resp = client.post(
            "/ai/regulatory-check",
            json={"text": "This document references 21 CFR Part 11 and ISO 13485."},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "citations_found" in data
        assert "results" in data
        assert "has_issues" in data

    def test_regulatory_check_proxies_to_fsv_when_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FSV is configured and reachable, regulatory check proxies to FSV."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv-mock:8080")

        fsv_payload: dict[str, Any] = {
            "citations_found": 2,
            "results": [
                {"citation": "21 CFR Part 11", "valid_format": True, "known": True, "issues": []},
                {"citation": "ISO 13485", "valid_format": True, "known": True, "issues": []},
            ],
            "has_issues": False,
        }

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=fsv_payload)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "docreview360.fsv_proxy.httpx.AsyncClient", return_value=mock_client
        ):
            headers = _alice_headers()
            resp = client.post(
                "/ai/regulatory-check",
                json={"text": "References 21 CFR Part 11 and ISO 13485."},
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["citations_found"] == 2
        assert data["has_issues"] is False
        assert len(data["results"]) == 2

    def test_regulatory_check_falls_back_on_fsv_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FSV throws, regulatory check falls back to internal implementation."""
        monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv-mock:8080")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("FSV unavailable"))

        with patch(
            "docreview360.fsv_proxy.httpx.AsyncClient", return_value=mock_client
        ):
            headers = _alice_headers()
            resp = client.post(
                "/ai/regulatory-check",
                json={"text": "References 21 CFR Part 11."},
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "citations_found" in data

    def test_regulatory_check_rejects_empty_text(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /ai/regulatory-check must return 422 for empty text regardless of FSV config."""
        monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)
        headers = _alice_headers()
        resp = client.post(
            "/ai/regulatory-check",
            json={"text": "   "},
            headers=headers,
        )
        assert resp.status_code == 422
