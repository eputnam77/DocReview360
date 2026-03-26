from pathlib import Path

import pytest
from docreview360.accessibility import audit_html

from services.document_checker import detect_anomalies, run_checks


def test_run_checks_flags_unquoted_attributes(tmp_path: Path) -> None:
    html = "<img alt=/> <button aria-label=/></button>"
    path = tmp_path / "doc.html"
    path.write_text(html, encoding="utf-8")
    result = run_checks(path)
    assert "image missing alt text" in result["accessibility"]
    assert "button missing label" in result["accessibility"]


def test_audit_html_flags_unquoted_attributes() -> None:
    html = "<img alt=/> <button aria-label=/></button>"
    issues = audit_html(html)
    assert "image missing alt text" in issues
    assert "button missing label" in issues


def test_detect_anomalies_rejects_non_numeric_threshold() -> None:
    with pytest.raises(TypeError, match="real number"):
        detect_anomalies("example text", threshold="0.5")
