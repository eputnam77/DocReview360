from docreview360 import plugin_marketplace


def test_list_available_sorted(monkeypatch):
    plugin_data = {"b": {}, "a": {}, "c": {}}
    monkeypatch.setattr(plugin_marketplace, "PLUGIN_DATA", plugin_data, raising=False)
    assert plugin_marketplace.list_available() == ["a", "b", "c"]
