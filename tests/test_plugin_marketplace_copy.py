"""Additional tests for :mod:`docreview360.plugin_marketplace`.

These tests focus on ensuring helper functions do not leak internal state.
"""

from docreview360.plugin_marketplace import PLUGIN_DATA, list_plugins_with_info


def test_list_plugins_with_info_returns_copies() -> None:
    """Modifying the returned plugin dictionaries must not mutate ``PLUGIN_DATA``."""

    plugins = list_plugins_with_info()
    assert plugins, "expected at least one plugin entry"

    plugin = plugins[0]
    plugin_id = plugin["id"]

    # Mutate fields in the returned object
    plugin["name"] = "changed"
    plugin.setdefault("tags", []).append("extra")

    # Original metadata should remain untouched
    original = PLUGIN_DATA[plugin_id]
    assert original["name"] != "changed"
    assert "extra" not in original["tags"]
