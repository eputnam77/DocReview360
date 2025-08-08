"""Plugin integration examples for DocReview360.

This module demonstrates how real PyPI packages can be integrated
into DocReview360's document processing and review workflows.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin integrations for DocReview360."""

    def __init__(self) -> None:
        self.available_plugins: Dict[str, Any] = {}
        self._load_plugins()

    def _load_plugins(self) -> None:
        """Load available plugins based on what's installed."""
        # Check for language-tool-python
        try:
            language_tool_python = importlib.import_module("language_tool_python")
            self.available_plugins["language-tool-python"] = language_tool_python
            logger.info("Language Tool Python plugin loaded successfully")
        except ImportError:
            logger.debug("Language Tool Python plugin not available")

        # Check for textstat
        try:
            textstat = importlib.import_module("textstat")
            self.available_plugins["textstat"] = textstat
            logger.info("TextStat plugin loaded successfully")
        except ImportError:
            logger.debug("TextStat plugin not available")

        # Check for PyPDF2
        try:
            PyPDF2 = importlib.import_module("PyPDF2")
            self.available_plugins["pypdf2"] = PyPDF2
            logger.info("PyPDF2 plugin loaded successfully")
        except ImportError:
            logger.debug("PyPDF2 plugin not available")

        # Check for python-docx
        try:
            docx = importlib.import_module("docx")
            self.available_plugins["python-docx"] = docx
            logger.info("Python-docx plugin loaded successfully")
        except ImportError:
            logger.debug("Python-docx plugin not available")

    def check_grammar_advanced(self, text: str) -> List[Dict[str, Any]]:
        """Advanced grammar checking using LanguageTool if available."""
        if "language-tool-python" not in self.available_plugins:
            logger.warning("Language Tool Python not available for advanced grammar checking")
            return []

        try:
            tool = self.available_plugins["language-tool-python"].LanguageTool('en-US')
            matches = tool.check(text)

            issues: List[Dict[str, Any]] = []
            for match in matches:
                issues.append({
                    "message": match.ruleId,
                    "description": match.message,
                    "suggestions": match.replacements[:3],  # Top 3 suggestions
                    "offset": match.offset,
                    "length": match.errorLength,
                    "severity": "error" if match.ruleId.startswith("MORFOLOGIK") else "warning"
                })

            tool.close()
            return issues
        except Exception as e:
            logger.error(f"Error in advanced grammar checking: {e}")
            return []

    def analyze_readability(self, text: str) -> Dict[str, Any]:
        """Analyze text readability using TextStat if available."""
        if "textstat" not in self.available_plugins:
            logger.warning("TextStat not available for readability analysis")
            return {}

        try:
            textstat = self.available_plugins["textstat"]

            return {
                "flesch_reading_ease": textstat.flesch_reading_ease(text),
                "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
                "gunning_fog": textstat.gunning_fog(text),
                "smog_index": textstat.smog_index(text),
                "automated_readability_index": textstat.automated_readability_index(text),
                "coleman_liau_index": textstat.coleman_liau_index(text),
                "linsear_write_formula": textstat.linsear_write_formula(text),
                "dale_chall_readability_score": textstat.dale_chall_readability_score(text),
                "difficult_words": textstat.difficult_words(text),
                "syllable_count": textstat.syllable_count(text),
                "lexicon_count": textstat.lexicon_count(text),
                "sentence_count": textstat.sentence_count(text),
                "char_count": textstat.char_count(text),
                "letter_count": textstat.letter_count(text)
            }
        except Exception as e:
            logger.error(f"Error in readability analysis: {e}")
            return {}

    def extract_pdf_text(self, pdf_path: str) -> Optional[str]:
        """Extract text from PDF using PyPDF2 if available."""
        if "pypdf2" not in self.available_plugins:
            logger.warning("PyPDF2 not available for PDF text extraction")
            return None

        try:
            PyPDF2 = self.available_plugins["pypdf2"]

            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return None

    def create_word_document(self, content: str, output_path: str) -> bool:
        """Create a Word document using python-docx if available."""
        if "python-docx" not in self.available_plugins:
            logger.warning("Python-docx not available for Word document creation")
            return False

        try:
            docx = self.available_plugins["python-docx"]
            doc = docx.Document()
            doc.add_paragraph(content)
            doc.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Error creating Word document: {e}")
            return False

    def get_plugin_status(self) -> Dict[str, bool]:
        """Get status of all available plugins."""
        return {
            plugin_name: True
            for plugin_name in self.available_plugins.keys()
        }


# Global plugin manager instance
plugin_manager = PluginManager()


def enhanced_document_check(document_content: str) -> Dict[str, Any]:
    """Enhanced document checking using available plugins."""
    results: Dict[str, Any] = {
        "basic_grammar": [],  # From existing grammar_plugin.py
        "advanced_grammar": [],
        "readability": {},
        "plugin_status": plugin_manager.get_plugin_status()
    }

    # Advanced grammar checking
    results["advanced_grammar"] = plugin_manager.check_grammar_advanced(document_content)

    # Readability analysis
    results["readability"] = plugin_manager.analyze_readability(document_content)

    return results
