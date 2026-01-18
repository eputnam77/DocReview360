import docreview360.plugin_marketplace as pm


def test_get_plugin_info_returns_copy():
    info = pm.get_plugin_info("weasyprint")
    assert info is not None
    info["name"] = "mutated"
    again = pm.get_plugin_info("weasyprint")
    assert again["name"] == "WeasyPrint"
