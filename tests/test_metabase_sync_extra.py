from types import SimpleNamespace

import httpx
from docreview360.metabase_sync import run_field_sync


def test_run_field_sync(monkeypatch):
    called = {}

    def fake_post(url, headers=None, timeout=None):
        called["url"] = url
        called["headers"] = headers
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(httpx, "post", fake_post)
    run_field_sync("http://example.com", "token")
    assert called["url"].endswith("/api/field/sync")
    assert called["headers"] == {"X-Metabase-Session": "token"}


def test_run_field_sync_early_returns():
    # invalid base_url
    run_field_sync("ftp://example", "token")
    # non-ascii token
    run_field_sync("http://example", "tok\u2603")


def test_run_field_sync_network_error(monkeypatch):
    def fail_post(*args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "post", fail_post)
    run_field_sync("http://example.com", "token")
