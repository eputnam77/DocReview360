from pathlib import Path

from docreview360 import accessibility
from services.document_checker import run_checks


def test_audit_html_accepts_unquoted_alt() -> None:
    html = '<img src="foo" alt=logo>'
    assert accessibility.audit_html(html) == []


def test_run_checks_accepts_unquoted_alt(tmp_path: Path) -> None:
    html = '<img src="foo" alt=logo>'
    file = tmp_path / "sample.html"
    file.write_text(html)
    result = run_checks(file)
    assert result["accessibility"] == []
