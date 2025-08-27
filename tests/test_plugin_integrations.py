from docreview360.plugin_integrations import PluginManager, enhanced_document_check


def test_plugin_manager_without_plugins(tmp_path):
    pm = PluginManager()
    pm.available_plugins.clear()
    assert pm.check_grammar_advanced("text") == []
    assert pm.analyze_readability("text") == {}
    assert pm.extract_pdf_text(str(tmp_path / "missing.pdf")) is None
    assert pm.create_word_document("hello", str(tmp_path / "out.docx")) is False
    assert pm.get_plugin_status() == {}
    res = enhanced_document_check("hi")
    assert "plugin_status" in res and res["advanced_grammar"] == []
