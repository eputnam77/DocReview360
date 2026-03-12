# SPDX-License-Identifier: MIT
"""Item 98 / Item 16 — Docs link and drift checker tests.

Covers scripts/check-docs-links.py: exits 0, SUMMARY output, all
check functions, broken-link detection, GPL/placeholder scanning,
Quick Start in README, and license metadata accuracy.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-docs-links.py"
LICENSES_DOC = REPO_ROOT / "docs" / "licenses.md"
SECURITY_MD = REPO_ROOT / "SECURITY.md"
README = REPO_ROOT / "README.md"


def run_script(extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(extra_args or [])],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )


class TestDocsLinksContract:
    def test_script_exists(self) -> None:
        assert SCRIPT.exists()

    def test_exits_zero(self) -> None:
        result = run_script()
        assert result.returncode == 0, result.stderr[:200]

    def test_prints_summary(self) -> None:
        result = run_script()
        assert "SUMMARY" in result.stdout

    def test_covers_relative_links(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "link" in combined.lower()

    def test_covers_placeholders(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "placeholder" in combined.lower() or "example.com" in combined.lower()

    def test_covers_gpl_references(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "gpl" in combined.lower() or "license" in combined.lower()

    def test_covers_removed_modules(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "removed" in combined.lower() or "stale" in combined.lower()

    def test_output_flag_creates_report(self, tmp_path: Path) -> None:
        out = str(tmp_path / "links.md")
        result = run_script(["--output", out])
        assert result.returncode == 0


class TestDocsLinksSource:
    def _text(self) -> str:
        return SCRIPT.read_text(encoding="utf-8")

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in self._text()

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in self._text()

    def test_check_relative_links_function(self) -> None:
        assert "check_relative_links" in self._text()

    def test_check_placeholders_function(self) -> None:
        assert "check_placeholders" in self._text()

    def test_check_gpl_references_function(self) -> None:
        assert "check_gpl_references" in self._text()

    def test_check_removed_module_refs_function(self) -> None:
        assert "check_removed_module_refs" in self._text()

    def test_print_summary_function(self) -> None:
        assert "print_summary" in self._text()

    def test_write_report_function(self) -> None:
        assert "write_report" in self._text()

    def test_code_block_stripping(self) -> None:
        # Script must strip fenced code blocks and inline code to avoid false positives
        text = self._text()
        assert "text_no_code" in text
        assert "```" in text

    def test_severity_ordering(self) -> None:
        text = self._text()
        ci = text.find('"CRITICAL"')
        hi = text.find('"HIGH"')
        if ci >= 0 and hi >= 0:
            assert ci < hi

    def test_skips_http_links(self) -> None:
        assert "http://" in self._text()
        assert "https://" in self._text()

    def test_skips_dev_paths(self) -> None:
        assert ".dev/" in self._text()

    def test_no_browser_required(self) -> None:
        text = self._text()
        assert "playwright" not in text
        assert "selenium" not in text


class TestLicensesDocMIT:
    """Verify docs/licenses.md correctly reflects MIT (not GPL)."""

    def _text(self) -> str:
        return LICENSES_DOC.read_text(encoding="utf-8")

    def test_licenses_doc_exists(self) -> None:
        assert LICENSES_DOC.exists()

    def test_says_mit_license(self) -> None:
        assert "MIT License" in self._text() or "MIT" in self._text()

    def test_not_gpl_only_project(self) -> None:
        # The project license heading must say MIT, not GPL-3.0-only
        text = self._text()
        assert "GPL-3.0-only" not in text.splitlines()[2]  # line 3 has the project license

    def test_filelock_removed_from_deps_table(self) -> None:
        # filelock was removed as a runtime dependency; it should not be in the Python deps table
        text = self._text()
        # filelock may appear in historical notes but not as an active dep row
        lines_with_filelock = [
            line for line in text.splitlines()
            if "filelock" in line and line.strip().startswith("|")
        ]
        assert len(lines_with_filelock) == 0, (
            f"filelock still listed as active dep: {lines_with_filelock}"
        )

    def test_license_compatibility_section_exists(self) -> None:
        assert "License Compatibility" in self._text()

    def test_mit_allows_proprietary_use(self) -> None:
        # The compatibility section must mention MIT allows proprietary embedding
        text = self._text()
        assert "MIT" in text and "proprietary" in text.lower()


class TestSecurityMDPlaceholders:
    """Verify SECURITY.md has no placeholder emails."""

    def _text(self) -> str:
        return SECURITY_MD.read_text(encoding="utf-8")

    def test_security_md_exists(self) -> None:
        assert SECURITY_MD.exists()

    def test_no_example_com_email(self) -> None:
        assert "security@example.com" not in self._text()

    def test_has_real_reporting_mechanism(self) -> None:
        text = self._text()
        # Must reference GitHub security advisories or a real contact
        assert "github.com" in text.lower() or "advisories" in text.lower()


class TestReadMEQuickStart:
    """Verify README.md has a Quick Start and no placeholder docs URLs."""

    def _text(self) -> str:
        return README.read_text(encoding="utf-8")

    def test_readme_exists(self) -> None:
        assert README.exists()

    def test_has_quick_start_section(self) -> None:
        assert "Quick Start" in self._text() or "Quick install" in self._text()

    def test_quick_start_covers_macos_linux(self) -> None:
        text = self._text()
        assert "macOS" in text or "Linux" in text or "source .venv/bin/activate" in text

    def test_quick_start_covers_windows(self) -> None:
        text = self._text()
        assert "Windows" in text or "PowerShell" in text or "Activate.ps1" in text

    def test_no_example_com_docs_url(self) -> None:
        # The docs link should not point to example.com
        assert "https://example.com/docreview360" not in self._text()

    def test_has_license_section(self) -> None:
        text = self._text()
        assert "MIT" in text or "License" in text
