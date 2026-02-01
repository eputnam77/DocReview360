"""Template linter toggle tests."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"


@pytest.fixture
def template_tools(monkeypatch: pytest.MonkeyPatch):
    pkg = types.ModuleType("docreview360")
    pkg.__path__ = [str(PACKAGE_DIR)]
    monkeypatch.setitem(sys.modules, "docreview360", pkg)

    spec_tt = importlib.util.spec_from_file_location(
        "docreview360.tiptap", PACKAGE_DIR / "tiptap.py"
    )
    tiptap = importlib.util.module_from_spec(spec_tt)
    monkeypatch.setitem(sys.modules, "docreview360.tiptap", tiptap)
    spec_tt.loader.exec_module(tiptap)

    spec_plugins = importlib.util.spec_from_file_location(
        "docreview360.tiptap_plugins", PACKAGE_DIR / "tiptap_plugins.py"
    )
    plugins = importlib.util.module_from_spec(spec_plugins)
    monkeypatch.setitem(sys.modules, "docreview360.tiptap_plugins", plugins)
    spec_plugins.loader.exec_module(plugins)

    return tiptap.markdown_to_tiptap, plugins.lint_template


def test_linter_reports_missing_heading_when_enabled(template_tools) -> None:
    markdown_to_tiptap, lint_template = template_tools
    data = markdown_to_tiptap("# 1 Intro")
    rules = {"required_headings": ["1.1 Purpose"]}
    issues = lint_template(data, rules, enabled=True)
    assert "missing heading '1.1 Purpose'" in issues
    assert lint_template(data, rules, enabled=False) == []
