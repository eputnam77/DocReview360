#!/usr/bin/env python3
"""Demonstration script for DocReview360 plugin integrations.

This script shows how real PyPI packages can enhance DocReview360's
document processing and review capabilities.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import docreview360
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docreview360.plugin_integrations import plugin_manager, enhanced_document_check


def demo_plugin_status() -> None:
    """Demonstrate plugin status checking."""
    print("🔌 Plugin Status Check")
    print("=" * 50)

    status = plugin_manager.get_plugin_status()
    if not status:
        print("❌ No plugins are currently available")
        print("💡 Install plugins from the Plugin Marketplace to enable enhanced features")
    else:
        print("✅ Available plugins:")
        for plugin_name, is_available in status.items():
            status_icon = "✅" if is_available else "❌"
            print(f"   {status_icon} {plugin_name}")
    print()


def demo_readability_analysis() -> None:
    """Demonstrate readability analysis."""
    print("📊 Readability Analysis Demo")
    print("=" * 50)

    sample_text = """
    The quick brown fox jumps over the lazy dog. This sentence contains all the letters
    of the English alphabet. It is commonly used for testing typing and readability.
    The Flesch Reading Ease score measures how easy a text is to read, with higher
    scores indicating easier reading.
    """

    result = plugin_manager.analyze_readability(sample_text)

    if result:
        print("✅ Readability analysis completed:")
        print(f"   • Flesch Reading Ease: {result.get('flesch_reading_ease', 'N/A'):.1f}")
        print(f"   • Flesch-Kincaid Grade: {result.get('flesch_kincaid_grade', 'N/A'):.1f}")
        print(f"   • Gunning Fog Index: {result.get('gunning_fog', 'N/A'):.1f}")
        print(f"   • Word Count: {result.get('lexicon_count', 'N/A')}")
        print(f"   • Sentence Count: {result.get('sentence_count', 'N/A')}")
        print(f"   • Character Count: {result.get('char_count', 'N/A')}")
    else:
        print("❌ Readability analysis not available")
        print("💡 Install 'textstat' plugin for readability analysis")
    print()


def demo_enhanced_document_check() -> None:
    """Demonstrate enhanced document checking."""
    print("🔍 Enhanced Document Check Demo")
    print("=" * 50)

    sample_text = "This is a test document with some content for analysis. The the word 'the' is repeated."

    result = enhanced_document_check(sample_text)

    print("✅ Document analysis completed:")
    print(f"   • Basic grammar issues: {len(result['basic_grammar'])}")
    print(f"   • Advanced grammar issues: {len(result['advanced_grammar'])}")
    print(f"   • Readability metrics: {len(result['readability'])} available")
    print(f"   • Available plugins: {len(result['plugin_status'])}")

    if result['basic_grammar']:
        print("   • Basic grammar issues found:")
        for issue in result['basic_grammar']:
            print(f"     - {issue}")

    if result['advanced_grammar']:
        print("   • Advanced grammar issues found:")
        for issue in result['advanced_grammar']:
            print(f"     - {issue['description']} (Rule: {issue['message']})")

    print()


def demo_plugin_installation_info() -> None:
    """Show information about plugin installation."""
    print("📦 Plugin Installation Information")
    print("=" * 50)

    print("To install plugins and enable enhanced features:")
    print("1. Go to Configuration → Plugin Marketplace in the DocReview360 UI")
    print("2. Click 'Install Plugin' for the plugins you want")
    print("3. Plugins will be installed via pip from PyPI")
    print()

    print("Recommended plugins for document review:")
    print("   • language-tool-python: Advanced grammar and style checking")
    print("   • textstat: Readability analysis and text statistics")
    print("   • pypdf2: PDF text extraction and manipulation")
    print("   • python-docx: Word document creation and modification")
    print("   • markdown: Markdown to HTML conversion")
    print("   • beautifulsoup4: HTML parsing and cleaning")
    print()


def main() -> None:
    """Run the plugin demonstration."""
    print("🚀 DocReview360 Plugin Integration Demo")
    print("=" * 60)
    print()

    demo_plugin_status()
    demo_readability_analysis()
    demo_enhanced_document_check()
    demo_plugin_installation_info()

    print("🎉 Demo completed!")
    print()
    print("For more information, visit the Plugin Marketplace in the DocReview360 UI.")


if __name__ == "__main__":
    main()
