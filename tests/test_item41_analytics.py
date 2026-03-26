# SPDX-License-Identifier: MIT
"""Tests for Item 41 analytics dashboard, exportable reports, and external search stub.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item41_analytics.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _alice_headers() -> dict[str, str]:
    """Return auth headers for alice (admin role)."""
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


def _manager_headers() -> dict[str, str]:
    """Return auth headers for mgr1 (manager role)."""
    try:
        auth.USER_REPOSITORY.create_user("mgr1", "Mgr1PassSecure!")
    except Exception:
        pass
    from docreview360 import rbac

    rbac.add_role("mgr1", "manager")
    token = auth.create_access_token({"sub": "mgr1"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _viewer_headers() -> dict[str, str]:
    """Return auth headers for viewer1 (no elevated role)."""
    try:
        auth.USER_REPOSITORY.create_user("viewer1", "View1PassSecure!")
    except Exception:
        pass
    token = auth.create_access_token({"sub": "viewer1"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests: GET /dashboard/analytics
# ---------------------------------------------------------------------------


class TestAnalyticsDashboardEndpoint:
    """Tests for GET /dashboard/analytics."""

    def test_requires_auth(self) -> None:
        """Unauthenticated request should return 401 or 403."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics")
        assert resp.status_code in {401, 403}

    def test_viewer_forbidden(self) -> None:
        """A plain viewer without manager/admin role must be rejected."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_viewer_headers())
        assert resp.status_code == 403

    def test_manager_can_access(self) -> None:
        """A user with the manager role should receive a 200 response."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_manager_headers())
        assert resp.status_code == 200

    def test_admin_can_access(self) -> None:
        """An admin user should receive a 200 response."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        assert resp.status_code == 200

    def test_response_contains_required_keys(self) -> None:
        """Response body must contain all required top-level keys."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        required = {"document_stats", "review_stats", "user_activity", "quality_trends", "phase_throughput"}
        assert required.issubset(data.keys()), f"Missing keys: {required - data.keys()}"

    def test_document_stats_subkeys(self) -> None:
        """document_stats must include total, by_status, by_type, and avg_age_days."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        doc_stats = resp.json()["document_stats"]
        assert "total" in doc_stats
        assert "by_status" in doc_stats
        assert "by_type" in doc_stats
        assert "avg_age_days" in doc_stats

    def test_review_stats_subkeys(self) -> None:
        """review_stats must include total_reviews, avg_completion_days, on_time_rate."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        review_stats = resp.json()["review_stats"]
        assert "total_reviews" in review_stats
        assert "avg_completion_days" in review_stats
        assert "on_time_rate" in review_stats

    def test_user_activity_subkeys(self) -> None:
        """user_activity must include active_users and total_actions_30d."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        user_activity = resp.json()["user_activity"]
        assert "active_users" in user_activity
        assert "total_actions_30d" in user_activity

    def test_quality_trends_is_list(self) -> None:
        """quality_trends must be a list."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        assert isinstance(resp.json()["quality_trends"], list)

    def test_phase_throughput_is_list(self) -> None:
        """phase_throughput must be a list."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        assert isinstance(resp.json()["phase_throughput"], list)

    def test_generated_at_present(self) -> None:
        """Response must include a generated_at timestamp."""
        client = TestClient(app)
        resp = client.get("/dashboard/analytics", headers=_alice_headers())
        assert "generated_at" in resp.json()

    def test_date_filter_params_accepted(self) -> None:
        """Passing start_date and end_date query params should not raise an error."""
        client = TestClient(app)
        resp = client.get(
            "/dashboard/analytics",
            params={"start_date": "2026-01-01T00:00:00", "end_date": "2026-12-31T23:59:59"},
            headers=_alice_headers(),
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: GET /reports/analytics/export
# ---------------------------------------------------------------------------


class TestAnalyticsExportEndpoint:
    """Tests for GET /reports/analytics/export."""

    def test_export_requires_admin(self) -> None:
        """Only admin role can export analytics; manager should be rejected."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export", headers=_manager_headers())
        assert resp.status_code == 403

    def test_export_json_default(self) -> None:
        """Default format is JSON and response body must be parseable."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "document_stats" in data

    def test_export_json_explicit(self) -> None:
        """format=json must return JSON content-type."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export?format=json", headers=_alice_headers())
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    def test_export_csv_content_type(self) -> None:
        """format=csv must return text/csv content-type."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export?format=csv", headers=_alice_headers())
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_csv_has_header_row(self) -> None:
        """CSV export body must start with the expected header row."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export?format=csv", headers=_alice_headers())
        assert resp.status_code == 200
        first_line = resp.text.splitlines()[0]
        assert "metric" in first_line
        assert "value" in first_line

    def test_export_csv_contains_total_documents(self) -> None:
        """CSV export must contain a total_documents row."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export?format=csv", headers=_alice_headers())
        assert "total_documents" in resp.text

    def test_export_invalid_format_returns_400(self) -> None:
        """An unsupported format value must return 400."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export?format=xml", headers=_alice_headers())
        assert resp.status_code == 400

    def test_export_unauthenticated_returns_401_or_403(self) -> None:
        """Unauthenticated request should return 401 or 403."""
        client = TestClient(app)
        resp = client.get("/reports/analytics/export")
        assert resp.status_code in {401, 403}


# ---------------------------------------------------------------------------
# Tests: is_external_search_configured() and config
# ---------------------------------------------------------------------------


class TestExternalSearchConfig:
    """Tests for the external search configuration helpers."""

    def test_not_configured_by_default(self, monkeypatch) -> None:
        """is_external_search_configured() returns False when no env vars set."""
        monkeypatch.delenv("DOCREVIEW360_SEARCH_BACKEND", raising=False)
        monkeypatch.delenv("OPENSEARCH_URL", raising=False)
        monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
        # Re-import to pick up monkeypatched env
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.is_external_search_configured() is False

    def test_not_configured_sqlite_backend(self, monkeypatch) -> None:
        """sqlite backend with a URL set is still not considered external."""
        monkeypatch.setenv("DOCREVIEW360_SEARCH_BACKEND", "sqlite")
        monkeypatch.setenv("OPENSEARCH_URL", "http://localhost:9200")
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.is_external_search_configured() is False

    def test_configured_when_opensearch_url_set(self, monkeypatch) -> None:
        """is_external_search_configured() returns True with opensearch + URL."""
        monkeypatch.setenv("DOCREVIEW360_SEARCH_BACKEND", "opensearch")
        monkeypatch.setenv("OPENSEARCH_URL", "http://localhost:9200")
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.is_external_search_configured() is True

    def test_configured_when_elasticsearch_url_set(self, monkeypatch) -> None:
        """is_external_search_configured() returns True with elasticsearch + URL."""
        monkeypatch.setenv("DOCREVIEW360_SEARCH_BACKEND", "elasticsearch")
        monkeypatch.setenv("ELASTICSEARCH_URL", "http://localhost:9200")
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.is_external_search_configured() is True

    def test_opensearch_without_url_not_configured(self, monkeypatch) -> None:
        """opensearch backend without a URL is not configured."""
        monkeypatch.setenv("DOCREVIEW360_SEARCH_BACKEND", "opensearch")
        monkeypatch.delenv("OPENSEARCH_URL", raising=False)
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.is_external_search_configured() is False

    def test_get_search_backend_default(self, monkeypatch) -> None:
        """get_search_backend() returns 'sqlite' when env var not set."""
        monkeypatch.delenv("DOCREVIEW360_SEARCH_BACKEND", raising=False)
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.get_search_backend() == "sqlite"

    def test_get_search_backend_opensearch(self, monkeypatch) -> None:
        """get_search_backend() returns 'opensearch' when configured."""
        monkeypatch.setenv("DOCREVIEW360_SEARCH_BACKEND", "opensearch")
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.get_search_backend() == "opensearch"

    def test_client_raises_when_no_url(self, monkeypatch) -> None:
        """ExternalSearchClient raises NotImplementedError when no URL configured."""
        monkeypatch.delenv("DOCREVIEW360_SEARCH_BACKEND", raising=False)
        monkeypatch.delenv("OPENSEARCH_URL", raising=False)
        monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        with pytest.raises(NotImplementedError, match="No external search backend"):
            _ext.ExternalSearchClient()

    def test_client_accepts_explicit_url(self, monkeypatch) -> None:
        """ExternalSearchClient can be instantiated with an explicit base_url."""
        monkeypatch.delenv("OPENSEARCH_URL", raising=False)
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        client = _ext.ExternalSearchClient(base_url="http://localhost:9200")
        assert client.base_url == "http://localhost:9200"
        assert client.index == "docreview360"

    def test_client_strips_trailing_slash(self, monkeypatch) -> None:
        """ExternalSearchClient strips trailing slash from base_url."""
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        client = _ext.ExternalSearchClient(base_url="http://localhost:9200/")
        assert client.base_url == "http://localhost:9200"

    def test_config_dataclass_has_search_fields(self) -> None:
        """Config dataclass must expose search_backend, opensearch_url, elasticsearch_url."""
        from docreview360.config import Config
        cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="jwt")
        assert cfg.search_backend == "sqlite"
        assert cfg.opensearch_url is None
        assert cfg.elasticsearch_url is None

    def test_get_external_url_none_for_sqlite(self, monkeypatch) -> None:
        """get_external_url() returns None when backend is sqlite."""
        monkeypatch.setenv("DOCREVIEW360_SEARCH_BACKEND", "sqlite")
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.get_external_url() is None

    def test_get_external_url_returns_opensearch_url(self, monkeypatch) -> None:
        """get_external_url() returns the OpenSearch URL when configured."""
        monkeypatch.setenv("DOCREVIEW360_SEARCH_BACKEND", "opensearch")
        monkeypatch.setenv("OPENSEARCH_URL", "http://search-host:9200")
        from importlib import reload

        import docreview360.search._external as _ext
        reload(_ext)
        assert _ext.get_external_url() == "http://search-host:9200"


# ---------------------------------------------------------------------------
# Tests: analytics_dashboard() function directly
# ---------------------------------------------------------------------------


class TestAnalyticsDashboardFunction:
    """Unit tests for reporting.analytics_dashboard()."""

    def test_returns_dict(self) -> None:
        """analytics_dashboard() must return a dict."""
        from docreview360.reporting import analytics_dashboard
        result = analytics_dashboard()
        assert isinstance(result, dict)

    def test_all_required_keys_present(self) -> None:
        """All required top-level keys must be present."""
        from docreview360.reporting import analytics_dashboard
        result = analytics_dashboard()
        required = {"generated_at", "period", "document_stats", "review_stats",
                    "user_activity", "quality_trends", "phase_throughput"}
        assert required.issubset(result.keys())

    def test_document_stats_total_is_int(self) -> None:
        """document_stats.total must be an int."""
        from docreview360.reporting import analytics_dashboard
        result = analytics_dashboard()
        assert isinstance(result["document_stats"]["total"], int)

    def test_on_time_rate_between_0_and_1(self) -> None:
        """on_time_rate must be between 0.0 and 1.0 inclusive."""
        from docreview360.reporting import analytics_dashboard
        result = analytics_dashboard()
        rate = result["review_stats"]["on_time_rate"]
        assert 0.0 <= rate <= 1.0

    def test_analytics_export_json(self) -> None:
        """analytics_export with fmt='json' returns valid JSON string."""
        import json

        from docreview360.reporting import analytics_export
        content, media_type = analytics_export(fmt="json")
        assert media_type == "application/json"
        data = json.loads(content)
        assert "document_stats" in data

    def test_analytics_export_csv(self) -> None:
        """analytics_export with fmt='csv' returns text/csv content."""
        from docreview360.reporting import analytics_export
        content, media_type = analytics_export(fmt="csv")
        assert media_type == "text/csv"
        assert "metric,value" in content
        assert "total_documents" in content
