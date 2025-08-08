"""Tests for plugin integrations."""

from __future__ import annotations

from docreview360.plugin_integrations import PluginManager, enhanced_document_check


def test_plugin_manager_initialization() -> None:
    """Test that PluginManager initializes correctly."""
    manager = PluginManager()
    assert isinstance(manager.available_plugins, dict)
    assert isinstance(manager.get_plugin_status(), dict)


def test_plugin_manager_without_plugins() -> None:
    """Test PluginManager behavior when no plugins are installed."""
    manager = PluginManager()

    # Test grammar checking without LanguageTool
    result = manager.check_grammar_advanced("This is a test sentence.")
    assert isinstance(result, list)

    # Test readability analysis (TextStat might be available)
    result = manager.analyze_readability("This is a test sentence.")
    assert isinstance(result, dict)

    # Test PDF extraction without PyPDF2
    result = manager.extract_pdf_text("nonexistent.pdf")
    assert result is None

    # Test Word document creation (python-docx might be available)
    result = manager.create_word_document("Test content", "test.docx")
    # Result could be True or False depending on whether python-docx is available
    assert isinstance(result, bool)


def test_enhanced_document_check() -> None:
    """Test the enhanced document check function."""
    test_content = "This is a test document with some content for analysis."

    result = enhanced_document_check(test_content)

    # Check that all expected keys are present
    expected_keys = ["basic_grammar", "advanced_grammar", "readability", "plugin_status"]
    for key in expected_keys:
        assert key in result

    # Check types
    assert isinstance(result["basic_grammar"], list)
    assert isinstance(result["advanced_grammar"], list)
    assert isinstance(result["readability"], dict)
    assert isinstance(result["plugin_status"], dict)


def test_plugin_status() -> None:
    """Test that plugin status is correctly reported."""
    manager = PluginManager()
    status = manager.get_plugin_status()

    # Status should be a dict mapping plugin names to boolean availability
    assert isinstance(status, dict)
    for plugin_name, is_available in status.items():
        assert isinstance(plugin_name, str)
        assert isinstance(is_available, bool)


def test_plugin_manager_error_handling() -> None:
    """Test that PluginManager handles errors gracefully."""
    manager = PluginManager()

    # Test with invalid PDF path
    result = manager.extract_pdf_text("/nonexistent/path/file.pdf")
    assert result is None

    # Test with invalid Word document path
    result = manager.create_word_document("content", "/invalid/path/file.docx")
    assert result is False
