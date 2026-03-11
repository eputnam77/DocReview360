# SPDX-License-Identifier: MIT
"""Tests for Item 41: integrations, plugin sandboxing, and WebSocket proxy docs."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# Confluence integration tests (offline — no network required)
# ---------------------------------------------------------------------------


class TestConfluenceIntegration:
    def test_client_from_env_raises_without_url(self, monkeypatch):
        monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
        from docreview360.integrations.confluence_integration import client_from_env, ConfluenceError

        with pytest.raises(ConfluenceError, match="CONFLUENCE_BASE_URL"):
            client_from_env()

    def test_client_construction(self):
        from docreview360.integrations.confluence_integration import ConfluenceClient

        client = ConfluenceClient(
            base_url="https://myorg.atlassian.net/wiki",
            username="user@example.com",
            api_token="secret",
            space_key="DOCS",
        )
        assert client.base_url == "https://myorg.atlassian.net/wiki"
        assert client.space_key == "DOCS"

    def test_auth_header(self):
        import base64
        from docreview360.integrations.confluence_integration import ConfluenceClient

        client = ConfluenceClient(
            base_url="https://example.atlassian.net/wiki",
            username="alice",
            api_token="token123",
        )
        header = client._auth_header()
        assert header.startswith("Basic ")
        decoded = base64.b64decode(header[6:]).decode()
        assert decoded == "alice:token123"

    def test_storage_to_markdown(self):
        from docreview360.integrations.confluence_integration import _storage_to_markdown

        html = "<h1>Title</h1><p>Hello <strong>world</strong>.</p>"
        md = _storage_to_markdown(html)
        assert "# Title" in md
        assert "**world**" in md

    def test_markdown_to_storage(self):
        from docreview360.integrations.confluence_integration import _markdown_to_storage

        md = "# My Page\n\nThis is **bold** text."
        storage = _markdown_to_storage(md)
        assert "<h1>My Page</h1>" in storage
        assert "<strong>bold</strong>" in storage

    def test_parse_page(self):
        from docreview360.integrations.confluence_integration import _parse_page

        resp = {
            "id": "12345",
            "title": "My Page",
            "space": {"key": "DOCS"},
            "version": {"number": 3},
            "body": {"storage": {"value": "<p>Content</p>"}},
            "_links": {"webui": "/wiki/spaces/DOCS/pages/12345"},
        }
        page = _parse_page(resp)
        assert page.id == "12345"
        assert page.title == "My Page"
        assert page.space_key == "DOCS"
        assert page.version == 3
        assert "Content" in page.body_storage


# ---------------------------------------------------------------------------
# Google Drive integration tests (offline)
# ---------------------------------------------------------------------------


class TestGoogleDriveIntegration:
    def test_client_from_env_with_direct_token(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_DRIVE_ACCESS_TOKEN", "test-token-abc")
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "folder-123")
        from docreview360.integrations.google_drive_integration import client_from_env

        client = client_from_env()
        assert client.access_token == "test-token-abc"
        assert client.default_folder_id == "folder-123"

    def test_client_from_env_raises_without_credentials(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_DRIVE_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", raising=False)
        from docreview360.integrations.google_drive_integration import client_from_env, GoogleDriveError

        with pytest.raises(GoogleDriveError):
            client_from_env()

    def test_client_construction(self):
        from docreview360.integrations.google_drive_integration import GoogleDriveClient

        client = GoogleDriveClient(access_token="tok", default_folder_id="fid")
        assert client.access_token == "tok"
        assert client.default_folder_id == "fid"

    def test_parse_file(self):
        from docreview360.integrations.google_drive_integration import _parse_file

        data = {
            "id": "file-abc",
            "name": "report.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size": "12345",
            "modifiedTime": "2026-03-10T12:00:00Z",
            "parents": ["folder-xyz"],
            "webViewLink": "https://drive.google.com/file/d/file-abc/view",
        }
        f = _parse_file(data)
        assert f.id == "file-abc"
        assert f.name == "report.docx"
        assert f.size == 12345
        assert f.parents == ["folder-xyz"]


# ---------------------------------------------------------------------------
# Plugin sandbox tests
# ---------------------------------------------------------------------------


class TestPluginSandbox:
    def test_direct_mode_success(self):
        from docreview360.plugin_sandbox import PluginSandbox

        sandbox = PluginSandbox(mode="none")
        result = sandbox.run(lambda x, y: x + y, 3, 4)
        assert result.success is True
        assert result.value == 7
        assert result.sandbox_mode == "none"

    def test_direct_mode_captures_exception(self):
        from docreview360.plugin_sandbox import PluginSandbox

        sandbox = PluginSandbox(mode="none")
        result = sandbox.run(lambda: 1 / 0)
        assert result.success is False
        assert "division by zero" in (result.error or "")

    def test_restricted_mode_success(self):
        from docreview360.plugin_sandbox import PluginSandbox

        sandbox = PluginSandbox(mode="restricted", timeout_seconds=5)
        result = sandbox.run(lambda: sum(range(100)))
        assert result.success is True
        assert result.value == 4950
        assert result.sandbox_mode == "restricted"

    def test_restricted_mode_blocks_os_import(self):
        from docreview360.plugin_sandbox import PluginSandbox

        def bad_plugin():
            import os as _os  # noqa: PLC0415
            return _os.listdir(".")

        sandbox = PluginSandbox(mode="restricted", timeout_seconds=5)
        result = sandbox.run(bad_plugin)
        assert result.success is False
        assert "os" in (result.error or "") or len(result.violations) > 0

    def test_restricted_mode_timeout(self):
        from docreview360.plugin_sandbox import PluginSandbox
        import time

        sandbox = PluginSandbox(mode="restricted", timeout_seconds=0.2)
        result = sandbox.run(lambda: time.sleep(10))
        assert result.success is False
        assert "timed out" in (result.error or "")

    def test_invalid_mode_raises(self):
        from docreview360.plugin_sandbox import PluginSandbox

        with pytest.raises(ValueError, match="sandbox mode"):
            PluginSandbox(mode="magic")

    def test_plugin_result_fields(self):
        from docreview360.plugin_sandbox import PluginResult

        r = PluginResult(success=True, value=42, elapsed_seconds=0.1, sandbox_mode="none")
        assert r.success is True
        assert r.value == 42

    def test_sandboxed_loader_registration(self):
        from docreview360.plugin_sandbox import SandboxedPluginLoader, PluginManifest

        loader = SandboxedPluginLoader()
        manifest = PluginManifest(
            name="test-plugin",
            module_path="json",  # stdlib module — always findable
            sandbox_mode="none",
            author="Test",
            version="1.0.0",
        )
        loader.register(manifest)
        plugins = loader.list_plugins()
        assert any(p["name"] == "test-plugin" for p in plugins)

    def test_sandboxed_loader_run_unknown_plugin(self):
        from docreview360.plugin_sandbox import SandboxedPluginLoader

        loader = SandboxedPluginLoader()
        result = loader.run("nonexistent", "some_func")
        assert result.success is False
        assert "not registered" in (result.error or "")


# ---------------------------------------------------------------------------
# Docs existence tests
# ---------------------------------------------------------------------------


class TestDocumentation:
    def test_websocket_proxy_guide_exists(self):
        import pathlib

        doc = pathlib.Path(__file__).parent.parent / "docs" / "websocket_proxy_guide.md"
        assert doc.exists(), "docs/websocket_proxy_guide.md is missing"
        content = doc.read_text()
        assert "nginx" in content.lower()
        assert "WebSocket" in content

    def test_api_versioning_doc_exists(self):
        import pathlib

        doc = pathlib.Path(__file__).parent.parent / "docs" / "api_versioning.md"
        assert doc.exists(), "docs/api_versioning.md is missing"
        content = doc.read_text()
        assert "v1" in content
        assert "breaking" in content.lower()

    def test_locale_files_exist(self):
        import json
        import pathlib

        locales_dir = pathlib.Path(__file__).parent.parent / "frontend" / "public" / "locales"
        for locale in ("en", "es", "fr", "de"):
            f = locales_dir / locale / "common.json"
            assert f.exists(), f"Missing locale file: {f}"
            data = json.loads(f.read_text())
            assert "nav" in data
            assert "common" in data

    def test_next_config_i18n(self):
        import pathlib

        cfg = pathlib.Path(__file__).parent.parent / "frontend" / "next.config.js"
        content = cfg.read_text()
        assert "i18n" in content
        assert '"en"' in content
        assert '"es"' in content
        assert '"fr"' in content
        assert '"de"' in content
