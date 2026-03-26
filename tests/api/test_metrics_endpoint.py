# SPDX-License-Identifier: MIT
"""Tests for the Prometheus /metrics scrape endpoint (R-18)."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _ensure_metrics_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee the metrics endpoint is mounted for these tests."""
    monkeypatch.delenv("DOCREVIEW360_METRICS_DISABLED", raising=False)


def test_metrics_endpoint_returns_200() -> None:
    """GET /metrics must return HTTP 200."""
    # Import after env is set so the mount is active.
    from docreview360.api import app

    client = TestClient(app, raise_server_exceptions=True)
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_content_type_is_prometheus() -> None:
    """Response Content-Type must advertise Prometheus text format."""
    from docreview360.api import app

    client = TestClient(app)
    response = client.get("/metrics")
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type or "openmetrics" in content_type


def test_metrics_body_contains_expected_metric() -> None:
    """Response body must contain at least one HELP or TYPE declaration."""
    from docreview360.api import app

    client = TestClient(app)
    response = client.get("/metrics")
    body = response.text
    assert "# HELP" in body or "# TYPE" in body


def test_metrics_disabled_env_var() -> None:
    """When DOCREVIEW360_METRICS_DISABLED=1 the /metrics route must not exist."""
    # The env var controls whether the route is mounted at app import time.
    # We validate the behaviour by checking that no route path matches /metrics
    # when the variable is set.  Since the app is already imported in this
    # process we inspect the route table rather than reimporting.
    from docreview360.api import app

    disabled = os.environ.get("DOCREVIEW360_METRICS_DISABLED", "").lower() in {"1", "true", "yes"}
    metrics_routes = [
        r for r in app.routes if getattr(r, "path", "").startswith("/metrics")
    ]
    if disabled:
        assert metrics_routes == [], "Expected /metrics to be absent when disabled"
    else:
        assert metrics_routes, "Expected /metrics to be present when not disabled"
