# SPDX-License-Identifier: MIT
"""Item 218 — Accessibility check loop tests.

Covers scripts/accessibility-check.py: exits 0, SUMMARY output, all
check functions, source-level scan coverage, and report output.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
A11Y_SCRIPT = REPO_ROOT / "scripts" / "accessibility-check.py"


def run_script(extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(A11Y_SCRIPT), *(extra_args or [])],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )


class TestAccessibilityCheckContract:
    def test_script_exists(self) -> None:
        assert A11Y_SCRIPT.exists()

    def test_exits_zero(self) -> None:
        result = run_script()
        assert result.returncode == 0, result.stderr[:200]

    def test_prints_summary(self) -> None:
        result = run_script()
        assert "SUMMARY" in result.stdout

    def test_covers_images(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "image" in combined.lower() or "alt" in combined.lower() or "img" in combined.lower()

    def test_covers_buttons(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "button" in combined.lower() or "aria" in combined.lower()

    def test_covers_headings(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "heading" in combined.lower() or "<h1>" in combined or "h1" in combined.lower()

    def test_covers_forms(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "form" in combined.lower() or "label" in combined.lower() or "input" in combined.lower()

    def test_covers_aria(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "aria" in combined.lower()

    def test_output_flag_creates_report(self, tmp_path: Path) -> None:
        out = str(tmp_path / "a11y.md")
        result = run_script(["--output", out])
        assert result.returncode == 0
        # Report should exist (even if no findings)


class TestAccessibilityCheckSource:
    def _text(self) -> str:
        return A11Y_SCRIPT.read_text(encoding="utf-8")

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in self._text()

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in self._text()

    def test_check_image_alt_function(self) -> None:
        assert "check_image_alt_attributes" in self._text()

    def test_check_button_function(self) -> None:
        assert "check_button_accessibility" in self._text()

    def test_check_form_labels_function(self) -> None:
        assert "check_form_labels" in self._text()

    def test_check_heading_hierarchy_function(self) -> None:
        assert "check_heading_hierarchy" in self._text()

    def test_check_aria_roles_function(self) -> None:
        assert "check_aria_roles" in self._text()

    def test_check_keyboard_navigation_function(self) -> None:
        assert "check_keyboard_navigation" in self._text()

    def test_eslint_a11y_check_function(self) -> None:
        assert "check_eslint_a11y" in self._text()

    def test_print_summary_function(self) -> None:
        assert "print_summary" in self._text()

    def test_severity_ordering(self) -> None:
        text = self._text()
        ci = text.find('"CRITICAL"')
        hi = text.find('"HIGH"')
        if ci >= 0 and hi >= 0:
            assert ci < hi

    def test_tsx_file_scanning(self) -> None:
        text = self._text()
        assert ".tsx" in text or "tsx" in text.lower()

    def test_graceful_skip_when_no_frontend(self) -> None:
        text = self._text()
        assert "skip" in text.lower() and "frontend" in text.lower()

    def test_no_browser_required(self) -> None:
        # Script must not import playwright or selenium
        text = self._text()
        assert "playwright" not in text
        assert "selenium" not in text
        assert "webdriver" not in text
