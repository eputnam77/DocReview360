"""Regression tests for the lightweight document checker fallback."""

from __future__ import annotations

from pathlib import Path

import pytest
from docreview360 import document_checker


def _write_and_check(tmp_path: Path, content: str) -> dict[str, object]:
    """Helper writing ``content`` to a file and running ``run_checks``."""

    path = tmp_path / "doc.html"
    path.write_text(content, encoding="utf-8")
    # Ensure the fallback implementation is exercised regardless of whether
    # FedStyleValidator is installed in the environment running the tests.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(document_checker, "_gov_run", None)
    try:
        return document_checker.run_checks(path)
    finally:
        monkeypatch.undo()


def test_img_without_attributes_triggers_accessibility_warning(tmp_path: Path) -> None:
    """Bare ``<img>`` tags should be flagged as missing alt text."""

    result = _write_and_check(tmp_path, "<img> Plain text")
    assert "image missing alt text" in result["accessibility"]


def test_blank_alt_attribute_is_treated_as_missing(tmp_path: Path) -> None:
    """An ``alt`` attribute containing only whitespace should be rejected."""

    result = _write_and_check(tmp_path, '<img alt="   ">')
    assert "image missing alt text" in result["accessibility"]


def test_unquoted_aria_label_is_respected(tmp_path: Path) -> None:
    """Buttons with unquoted ``aria-label`` values must not be flagged."""

    result = _write_and_check(tmp_path, "<button aria-label=Submit></button>")
    assert "button missing label" not in result["accessibility"]
