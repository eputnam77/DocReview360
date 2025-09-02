from pathlib import Path
from types import SimpleNamespace
import importlib

from docreview360.plugin_integrations import (
    PluginManager,
    enhanced_document_check,
)


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


def test_plugin_manager_with_plugins(tmp_path):
    pm = PluginManager()
    # stub language tool
    class Match:
        ruleId = "RULE"
        message = "msg"
        replacements = ["a", "b", "c"]
        offset = 0
        errorLength = 1

    class DummyTool:
        def __init__(self, lang: str) -> None:
            pass

        def check(self, text: str):
            return [Match]

        def close(self) -> None:
            pass

    pm.available_plugins["language-tool-python"] = SimpleNamespace(LanguageTool=DummyTool)

    # stub textstat
    pm.available_plugins["textstat"] = SimpleNamespace(
        flesch_reading_ease=lambda t: 1.0,
        flesch_kincaid_grade=lambda t: 2.0,
        gunning_fog=lambda t: 3.0,
        smog_index=lambda t: 4.0,
        automated_readability_index=lambda t: 5.0,
        coleman_liau_index=lambda t: 6.0,
        linsear_write_formula=lambda t: 7.0,
        dale_chall_readability_score=lambda t: 8.0,
        difficult_words=lambda t: 9,
        syllable_count=lambda t: 10,
        lexicon_count=lambda t: 11,
        sentence_count=lambda t: 12,
        char_count=lambda t: 13,
        letter_count=lambda t: 14,
    )

    # stub PyPDF2
    class DummyReader:
        def __init__(self, fh) -> None:
            self.pages = [SimpleNamespace(extract_text=lambda: "hi")]

    pm.available_plugins["pypdf2"] = SimpleNamespace(PdfReader=DummyReader)
    pdf = tmp_path / "doc.pdf"
    pdf.write_text("placeholder", encoding="utf-8")
    assert pm.extract_pdf_text(str(pdf)) == "hi\n"

    # stub python-docx
    class DummyDoc:
        def __init__(self) -> None:
            self.content: list[str] = []

        def add_paragraph(self, text: str) -> None:
            self.content.append(text)

        def save(self, path: str) -> None:
            Path(path).write_text("\n".join(self.content), encoding="utf-8")

    pm.available_plugins["python-docx"] = SimpleNamespace(Document=DummyDoc)
    out = tmp_path / "out.docx"
    assert pm.create_word_document("hello", str(out)) is True
    assert out.read_text(encoding="utf-8") == "hello"

    issues = pm.check_grammar_advanced("bad")
    assert issues and issues[0]["message"] == "RULE"
    readability = pm.analyze_readability("bad")
    assert readability["flesch_reading_ease"] == 1.0
    status = pm.get_plugin_status()
    assert status == {name: True for name in pm.available_plugins}


def test_extract_pdf_text_handles_none(tmp_path):
    pm = PluginManager()
    # Create a reader whose page returns ``None`` from ``extract_text``
    class DummyReader:
        def __init__(self, fh) -> None:
            self.pages = [SimpleNamespace(extract_text=lambda: None)]

    pm.available_plugins["pypdf2"] = SimpleNamespace(PdfReader=DummyReader)
    pdf = tmp_path / "doc.pdf"
    pdf.write_text("placeholder", encoding="utf-8")

    # Should not raise and should return a string (just a newline)
    assert pm.extract_pdf_text(str(pdf)) == "\n"


def test_plugin_load_branches(monkeypatch):
    def fake_import(name: str):
        if name == "textstat" or name == "docx":
            raise ImportError
        return SimpleNamespace()

    monkeypatch.setattr(importlib, "import_module", fake_import)
    pm = PluginManager()
    assert "textstat" not in pm.available_plugins
    assert "python-docx" not in pm.available_plugins
