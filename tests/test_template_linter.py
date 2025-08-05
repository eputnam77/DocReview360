"""Template linter toggle tests."""

# mypy: ignore-errors

import importlib.util
import sys
import types
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"
pkg = types.ModuleType("docreview360")
pkg.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("docreview360", pkg)

spec_tt = importlib.util.spec_from_file_location("docreview360.tiptap", PACKAGE_DIR / "tiptap.py")
tiptap = importlib.util.module_from_spec(spec_tt)
sys.modules["docreview360.tiptap"] = tiptap
spec_tt.loader.exec_module(tiptap)

spec_plugins = importlib.util.spec_from_file_location(
    "docreview360.tiptap_plugins", PACKAGE_DIR / "tiptap_plugins.py"
)
plugins = importlib.util.module_from_spec(spec_plugins)
sys.modules["docreview360.tiptap_plugins"] = plugins
spec_plugins.loader.exec_module(plugins)

markdown_to_tiptap = tiptap.markdown_to_tiptap
lint_template = plugins.lint_template


def test_linter_reports_missing_heading_when_enabled() -> None:
    data = markdown_to_tiptap("# 1 Intro")
    rules = {"required_headings": ["1.1 Purpose"]}
    issues = lint_template(data, rules, enabled=True)
    assert "missing heading '1.1 Purpose'" in issues
    assert lint_template(data, rules, enabled=False) == []

