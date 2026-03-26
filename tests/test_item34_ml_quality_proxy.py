# SPDX-License-Identifier: MIT
"""Item 34 Phase 1 — FSV proxy for POST /ml/quality.

Tests cover:
- POST /ml/quality returns "source": "internal" when FSV not configured
- POST /ml/quality returns "source": "fsv" when FSV configured and reachable
- POST /ml/quality falls back to "internal" when FSV configured but request fails
- QualityAssessmentResponse always has a "source" field
- FSV response fields are correctly mapped (score, flags, high_risk_terms)

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item34_ml_quality_proxy.py -v
"""

from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_ml_rate_limiter() -> None:
    """Reset the ML rate limiter before every test to prevent 429 bleed-over."""
    from docreview360.api.ml import reset_rate_limiter_for_testing
    reset_rate_limiter_for_testing()


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


_QUALITY_PAYLOAD = {"text": "This document contains several important policy requirements."}


# ---------------------------------------------------------------------------
# Test: source=internal when FSV not configured
# ---------------------------------------------------------------------------


def test_quality_source_internal_when_fsv_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /ml/quality returns source='internal' when FSV URL is not set."""
    monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)

    resp = client.post("/ml/quality", json=_QUALITY_PAYLOAD, headers=_alice_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert "source" in body
    assert body["source"] == "internal"


def test_quality_response_has_required_fields_internal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Internal path response includes score, raw_score, flags, high_risk_terms, source."""
    monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)

    resp = client.post("/ml/quality", json=_QUALITY_PAYLOAD, headers=_alice_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body
    assert "raw_score" in body
    assert "flags" in body
    assert isinstance(body["flags"], dict)
    assert "high_risk_terms" in body
    assert isinstance(body["high_risk_terms"], list)
    assert body["source"] == "internal"


# ---------------------------------------------------------------------------
# Test: source=fsv when FSV configured and reachable
# ---------------------------------------------------------------------------


def test_quality_source_fsv_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /ml/quality returns source='fsv' when FSV URL is configured."""
    monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv.test")

    _fsv_response = {
        "score": 0.85,
        "raw_score": 0.83,
        "flags": {"clarity": 0.9, "completeness": 0.8},
        "high_risk_terms": ["must", "shall"],
        "model": {"version": "1.0"},
    }

    with patch(
        "docreview360.api.ml.fsv_quality",
        new_callable=AsyncMock,
        return_value=_fsv_response,
    ):
        resp = client.post("/ml/quality", json=_QUALITY_PAYLOAD, headers=_alice_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fsv"
    assert body["score"] == pytest.approx(0.85)
    assert body["raw_score"] == pytest.approx(0.83)
    assert body["flags"] == {"clarity": pytest.approx(0.9), "completeness": pytest.approx(0.8)}
    assert "must" in body["high_risk_terms"]
    assert "shall" in body["high_risk_terms"]


def test_quality_fsv_maps_high_risk_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    """FSV high_risk_terms list is forwarded correctly in the response."""
    monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv.test")

    _fsv_response = {
        "score": 0.5,
        "raw_score": 0.5,
        "flags": {},
        "high_risk_terms": ["classified", "sensitive"],
    }

    with patch(
        "docreview360.api.ml.fsv_quality",
        new_callable=AsyncMock,
        return_value=_fsv_response,
    ):
        resp = client.post("/ml/quality", json=_QUALITY_PAYLOAD, headers=_alice_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fsv"
    assert set(body["high_risk_terms"]) == {"classified", "sensitive"}


# ---------------------------------------------------------------------------
# Test: fallback to internal when FSV configured but fails
# ---------------------------------------------------------------------------


def test_quality_fallback_to_internal_on_fsv_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /ml/quality falls back to internal when FSV call raises an exception."""
    monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv.test")

    with patch(
        "docreview360.api.ml.fsv_quality",
        new_callable=AsyncMock,
        side_effect=Exception("FSV unavailable"),
    ):
        resp = client.post("/ml/quality", json=_QUALITY_PAYLOAD, headers=_alice_headers())

    assert resp.status_code == 200
    body = resp.json()
    # Fell back to internal implementation
    assert body["source"] == "internal"


# ---------------------------------------------------------------------------
# Test: is_fsv_configured integration
# ---------------------------------------------------------------------------


def test_quality_fsv_not_called_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """fsv_quality is never invoked when FEDERAL_STYLE_VALIDATOR_URL is absent."""
    monkeypatch.delenv("FEDERAL_STYLE_VALIDATOR_URL", raising=False)

    with patch(
        "docreview360.api.ml.fsv_quality",
        new_callable=AsyncMock,
    ) as mock_fsv:
        resp = client.post("/ml/quality", json=_QUALITY_PAYLOAD, headers=_alice_headers())

    assert resp.status_code == 200
    mock_fsv.assert_not_called()


# ---------------------------------------------------------------------------
# Test: minimal FSV response (missing optional fields handled gracefully)
# ---------------------------------------------------------------------------


def test_quality_fsv_minimal_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /ml/quality handles FSV responses that omit optional fields."""
    monkeypatch.setenv("FEDERAL_STYLE_VALIDATOR_URL", "http://fsv.test")

    # FSV returns only 'score'; no raw_score, flags, or high_risk_terms
    _fsv_response: dict = {"score": 0.7}

    with patch(
        "docreview360.api.ml.fsv_quality",
        new_callable=AsyncMock,
        return_value=_fsv_response,
    ):
        resp = client.post("/ml/quality", json=_QUALITY_PAYLOAD, headers=_alice_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fsv"
    assert body["score"] == pytest.approx(0.7)
    # raw_score defaults to score when absent
    assert body["raw_score"] == pytest.approx(0.7)
    assert isinstance(body["flags"], dict)
    assert isinstance(body["high_risk_terms"], list)
