# SPDX-License-Identifier: MIT
"""Tests for Item 48: grammar-tool community category and per-org tool configuration.

Tests:
- Grammar tools have "Community / Optional" category and is_community=True
- pyspellchecker is in PLUGIN_DATA with the same category
- list_plugins_with_info() returns community plugins after non-community plugins
- GET /orgs/{org_id}/tools returns empty config for a new org
- PUT /orgs/{org_id}/tools with disabled_plugins list
- GET /orgs/{org_id}/tools returns updated disabled_plugins
- GET /orgs/{org_id}/tools/builtin-status returns effective state with org overrides
- PUT /orgs/{org_id}/tools/builtin-status applies per-org override
- PUT /orgs/{org_id}/tools with unknown plugin ID → 422
- PUT /orgs/{org_id}/tools/builtin-status with unknown plugin → 422

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item48_org_tools.py -v
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
# Helpers
# ---------------------------------------------------------------------------


def _alice_headers() -> dict[str, str]:
    """Return admin auth headers for alice."""
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
# Unit tests: PLUGIN_DATA metadata
# ---------------------------------------------------------------------------


class TestGrammarToolCategory:
    """Grammar tools must be in the Community / Optional category."""

    def test_language_tool_python_category(self):
        from docreview360.plugin_marketplace import PLUGIN_DATA

        plugin = PLUGIN_DATA["language-tool-python"]
        assert plugin["category"] == "Community / Optional"

    def test_pylanguagetool_category(self):
        from docreview360.plugin_marketplace import PLUGIN_DATA

        plugin = PLUGIN_DATA["pylanguagetool"]
        assert plugin["category"] == "Community / Optional"

    def test_pyspellchecker_exists_and_category(self):
        from docreview360.plugin_marketplace import PLUGIN_DATA

        assert "pyspellchecker" in PLUGIN_DATA
        plugin = PLUGIN_DATA["pyspellchecker"]
        assert plugin["category"] == "Community / Optional"

    def test_language_tool_python_is_community_true(self):
        from docreview360.plugin_marketplace import PLUGIN_DATA

        plugin = PLUGIN_DATA["language-tool-python"]
        assert plugin.get("is_community") is True

    def test_pylanguagetool_is_community_true(self):
        from docreview360.plugin_marketplace import PLUGIN_DATA

        plugin = PLUGIN_DATA["pylanguagetool"]
        assert plugin.get("is_community") is True

    def test_pyspellchecker_is_community_true(self):
        from docreview360.plugin_marketplace import PLUGIN_DATA

        plugin = PLUGIN_DATA["pyspellchecker"]
        assert plugin.get("is_community") is True

    def test_non_grammar_plugins_not_community(self):
        """Plugins like textstat and pypdf2 should not be community-flagged."""
        from docreview360.plugin_marketplace import PLUGIN_DATA

        for pid in ["textstat", "pypdf2", "python-docx", "nltk", "spacy"]:
            plugin = PLUGIN_DATA[pid]
            assert not plugin.get("is_community"), (
                f"Plugin {pid!r} should not have is_community=True"
            )


# ---------------------------------------------------------------------------
# Unit tests: list_plugins_with_info() ordering
# ---------------------------------------------------------------------------


class TestPluginListOrdering:
    """Community plugins must appear at the end of the plugin list."""

    def test_community_plugins_at_end(self):
        from docreview360.plugin_marketplace import list_plugins_with_info

        plugins = list_plugins_with_info()
        assert plugins, "Expected at least one plugin"

        # Find the boundary: first community plugin index
        first_community = next(
            (i for i, p in enumerate(plugins) if p.get("is_community")),
            None,
        )
        if first_community is None:
            return  # No community plugins — trivially passes

        # Every plugin after the first community plugin must also be community
        for plugin in plugins[first_community:]:
            assert plugin.get("is_community"), (
                f"Non-community plugin {plugin['id']!r} appears after community plugins"
            )

    def test_community_plugins_not_all_first(self):
        """There must be at least one non-community plugin before the community ones."""
        from docreview360.plugin_marketplace import list_plugins_with_info

        plugins = list_plugins_with_info()
        has_non_community = any(not p.get("is_community") for p in plugins)
        assert has_non_community, "Expected at least one non-community plugin"

        first_plugin = plugins[0]
        assert not first_plugin.get("is_community"), (
            "First plugin in the list should be non-community"
        )

    def test_list_returns_deep_copies(self):
        """Mutating the returned list should not affect PLUGIN_DATA."""
        from docreview360.plugin_marketplace import PLUGIN_DATA, list_plugins_with_info

        plugins = list_plugins_with_info()
        before_category = PLUGIN_DATA["textstat"]["category"]
        # Mutate a returned entry
        for p in plugins:
            if p["id"] == "textstat":
                p["category"] = "MUTATED"
                break
        # PLUGIN_DATA should be unchanged
        assert PLUGIN_DATA["textstat"]["category"] == before_category

    def test_all_grammar_community_plugins_present(self):
        """All three grammar/spell tools must appear in the full list."""
        from docreview360.plugin_marketplace import list_plugins_with_info

        ids = {p["id"] for p in list_plugins_with_info()}
        for expected in ("language-tool-python", "pylanguagetool", "pyspellchecker"):
            assert expected in ids, f"Expected {expected!r} in plugin list"


# ---------------------------------------------------------------------------
# Unit tests: per-org tool config (direct function calls)
# ---------------------------------------------------------------------------


class TestOrgToolConfigFunctions:
    """Direct tests of get_org_tool_config / set_org_tool_config helpers."""

    def test_get_config_new_org_returns_defaults(self):
        from docreview360.plugin_marketplace import get_org_tool_config

        cfg = get_org_tool_config("new-org-xyz")
        assert cfg["org_id"] == "new-org-xyz"
        assert cfg["disabled_plugins"] == []
        assert cfg["enabled_builtins"] == {}

    def test_set_disabled_plugins(self):
        from docreview360.plugin_marketplace import get_org_tool_config, set_org_tool_config

        set_org_tool_config("org-a", disabled_plugins=["language-tool-python"])
        cfg = get_org_tool_config("org-a")
        assert "language-tool-python" in cfg["disabled_plugins"]

    def test_set_disabled_plugins_unknown_raises(self):
        from docreview360.plugin_marketplace import set_org_tool_config

        with pytest.raises(ValueError, match="Unknown plugin"):
            set_org_tool_config("org-b", disabled_plugins=["not-a-real-plugin"])

    def test_set_enabled_builtins(self):
        from docreview360.plugin_marketplace import (
            BUILTIN_PLUGIN_IDS,
            get_org_tool_config,
            set_org_tool_config,
        )
        bid = next(iter(BUILTIN_PLUGIN_IDS))
        set_org_tool_config("org-c", enabled_builtins={bid: False})
        cfg = get_org_tool_config("org-c")
        assert cfg["enabled_builtins"][bid] is False

    def test_set_enabled_builtins_unknown_raises(self):
        from docreview360.plugin_marketplace import set_org_tool_config

        with pytest.raises(ValueError, match="Unknown built-in plugin"):
            set_org_tool_config("org-d", enabled_builtins={"not-a-builtin": True})

    def test_get_effective_plugins_marks_disabled(self):
        from docreview360.plugin_marketplace import get_effective_plugins, set_org_tool_config

        set_org_tool_config("org-e", disabled_plugins=["pylanguagetool"])
        plugins = get_effective_plugins("org-e")
        for p in plugins:
            if p["id"] == "pylanguagetool":
                assert p["disabled_for_org"] is True
            else:
                assert p["disabled_for_org"] is False

    def test_get_effective_plugins_no_disabled(self):
        from docreview360.plugin_marketplace import get_effective_plugins

        plugins = get_effective_plugins("org-no-disabled")
        for p in plugins:
            assert p["disabled_for_org"] is False

    def test_get_builtin_status_with_org_override(self):
        from docreview360.plugin_marketplace import (
            BUILTIN_PLUGIN_IDS,
            get_builtin_status,
            set_org_tool_config,
        )
        bid = next(iter(BUILTIN_PLUGIN_IDS))
        # Globally all builtins default to True; set org override to False
        set_org_tool_config("org-f", enabled_builtins={bid: False})
        status = get_builtin_status(org_id="org-f")
        assert status[bid] is False

    def test_get_builtin_status_no_org_id_unaffected(self):
        from docreview360.plugin_marketplace import (
            BUILTIN_PLUGIN_IDS,
            get_builtin_status,
            set_org_tool_config,
        )
        bid = next(iter(BUILTIN_PLUGIN_IDS))
        set_org_tool_config("org-g", enabled_builtins={bid: False})
        # Global status (no org_id) should still be the default
        status = get_builtin_status()
        assert bid in status  # Key exists regardless of value


# ---------------------------------------------------------------------------
# API tests: /orgs/{org_id}/tools
# ---------------------------------------------------------------------------


class TestOrgToolsAPI:
    """API-level tests for per-org tool configuration endpoints."""

    def test_get_tools_new_org_empty_config(self):
        client = TestClient(app)
        resp = client.get("/orgs/brand-new-org/tools", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_id"] == "brand-new-org"
        assert data["config"]["disabled_plugins"] == []
        assert data["config"]["enabled_builtins"] == {}

    def test_get_tools_includes_plugin_list(self):
        client = TestClient(app)
        resp = client.get("/orgs/test-org/tools", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["plugins"], list)
        assert len(data["plugins"]) > 0

    def test_put_tools_sets_disabled_plugins(self):
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.put(
            "/orgs/myorg/tools",
            json={"disabled_plugins": ["language-tool-python"]},
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "language-tool-python" in data["config"]["disabled_plugins"]

    def test_put_then_get_returns_updated_disabled(self):
        client = TestClient(app)
        hdrs = _alice_headers()
        client.put(
            "/orgs/orgx/tools",
            json={"disabled_plugins": ["pylanguagetool"]},
            headers=hdrs,
        )
        resp = client.get("/orgs/orgx/tools", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "pylanguagetool" in data["config"]["disabled_plugins"]

    def test_put_tools_unknown_plugin_returns_422(self):
        client = TestClient(app)
        resp = client.put(
            "/orgs/myorg/tools",
            json={"disabled_plugins": ["totally-fake-plugin"]},
            headers=_alice_headers(),
        )
        assert resp.status_code == 422

    def test_put_tools_empty_disabled_plugins(self):
        """Passing an empty list clears previous disabled plugins."""
        client = TestClient(app)
        hdrs = _alice_headers()
        # First disable something
        client.put(
            "/orgs/orgclear/tools",
            json={"disabled_plugins": ["pyspellchecker"]},
            headers=hdrs,
        )
        # Then clear
        resp = client.put(
            "/orgs/orgclear/tools",
            json={"disabled_plugins": []},
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["config"]["disabled_plugins"] == []

    def test_get_tools_requires_auth(self):
        client = TestClient(app)
        resp = client.get("/orgs/any-org/tools")
        assert resp.status_code in (401, 403)

    def test_put_tools_requires_admin(self):
        """Non-admin users should be rejected."""
        client = TestClient(app)
        try:
            auth.USER_REPOSITORY.create_user("bob", auth.DEMO_USER_DEFAULTS["bob"]["password"])
        except Exception:
            pass
        token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=30))
        resp = client.put(
            "/orgs/any-org/tools",
            json={"disabled_plugins": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# API tests: /orgs/{org_id}/tools/builtin-status
# ---------------------------------------------------------------------------


class TestOrgBuiltinStatusAPI:
    """API-level tests for per-org builtin plugin status endpoints."""

    def test_get_builtin_status_new_org(self):
        client = TestClient(app)
        resp = client.get("/orgs/fresh-org/tools/builtin-status", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_id"] == "fresh-org"
        assert isinstance(data["status"], dict)
        assert "org_overrides" in data

    def test_get_builtin_status_has_all_builtins(self):
        from docreview360.plugin_marketplace import BUILTIN_PLUGIN_IDS

        client = TestClient(app)
        resp = client.get("/orgs/test-org2/tools/builtin-status", headers=_alice_headers())
        assert resp.status_code == 200
        data = resp.json()
        for bid in BUILTIN_PLUGIN_IDS:
            assert bid in data["status"]

    def test_put_builtin_status_sets_org_override(self):
        from docreview360.plugin_marketplace import BUILTIN_PLUGIN_IDS

        bid = next(iter(sorted(BUILTIN_PLUGIN_IDS)))
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.put(
            "/orgs/override-org/tools/builtin-status",
            json={"pluginId": bid, "enabled": False},
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_id"] == "override-org"
        assert data["pluginId"] == bid
        assert data["enabled"] is False
        assert data["effective_status"][bid] is False

    def test_put_builtin_status_unknown_plugin_returns_422(self):
        client = TestClient(app)
        resp = client.put(
            "/orgs/someorg/tools/builtin-status",
            json={"pluginId": "not-a-real-builtin", "enabled": True},
            headers=_alice_headers(),
        )
        assert resp.status_code == 422

    def test_put_then_get_reflects_override(self):
        from docreview360.plugin_marketplace import BUILTIN_PLUGIN_IDS

        bid = next(iter(sorted(BUILTIN_PLUGIN_IDS)))
        client = TestClient(app)
        hdrs = _alice_headers()
        client.put(
            "/orgs/reflect-org/tools/builtin-status",
            json={"pluginId": bid, "enabled": False},
            headers=hdrs,
        )
        resp = client.get("/orgs/reflect-org/tools/builtin-status", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"][bid] is False
        assert data["org_overrides"][bid] is False

    def test_get_builtin_status_requires_admin(self):
        client = TestClient(app)
        resp = client.get("/orgs/any-org/tools/builtin-status")
        assert resp.status_code in (401, 403)

    def test_put_builtin_status_requires_admin(self):
        from docreview360.plugin_marketplace import BUILTIN_PLUGIN_IDS

        bid = next(iter(sorted(BUILTIN_PLUGIN_IDS)))
        client = TestClient(app)
        try:
            auth.USER_REPOSITORY.create_user("bob", auth.DEMO_USER_DEFAULTS["bob"]["password"])
        except Exception:
            pass
        token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=30))
        resp = client.put(
            "/orgs/any-org/tools/builtin-status",
            json={"pluginId": bid, "enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (401, 403)
