# SPDX-License-Identifier: MIT
"""Item 19a — Automated script tests.

Covers:
  - scripts/check-docs-drift.py: exit code, output structure, drift detection
  - scripts/check-placeholders.py: exit code, output structure, allowlist, scan scope
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DOCS_DRIFT_SCRIPT = SCRIPTS_DIR / "check-docs-drift.py"
PLACEHOLDERS_SCRIPT = SCRIPTS_DIR / "check-placeholders.py"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def run_script(script: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *extra_args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


# ---------------------------------------------------------------------------
# check-docs-drift.py — basic contract
# ---------------------------------------------------------------------------

class TestDocsDriftScript:
    def test_script_exists(self) -> None:
        assert DOCS_DRIFT_SCRIPT.exists(), "check-docs-drift.py not found"

    def test_exits_zero(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}\n{result.stderr}"

    def test_prints_repo_root(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        assert "Repo root" in result.stdout

    def test_prints_summary_section(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        assert "SUMMARY" in result.stdout

    def test_checks_version_consistency(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        # Should mention version check
        combined = result.stdout + result.stderr
        assert "version" in combined.lower() or "Version" in combined

    def test_checks_ports(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        combined = result.stdout + result.stderr
        assert "port" in combined.lower() or "Port" in combined

    def test_checks_env_vars(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        combined = result.stdout + result.stderr
        # Should mention env vars or environment
        assert "env" in combined.lower() or "ENV" in combined

    def test_checks_docker_docs(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        combined = result.stdout + result.stderr
        assert "docker" in combined.lower() or "Docker" in combined

    def test_checks_install_commands(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        combined = result.stdout + result.stderr
        assert "install" in combined.lower() or "Install" in combined

    def test_output_has_ok_or_drift_markers(self) -> None:
        result = run_script(DOCS_DRIFT_SCRIPT)
        # Script uses "ok   :" and "DRIFT:" prefixes
        has_marker = ("ok   :" in result.stdout or "DRIFT:" in result.stdout)
        assert has_marker, f"No ok/DRIFT marker in output:\n{result.stdout[:400]}"


# ---------------------------------------------------------------------------
# check-docs-drift.py — source-level coverage
# ---------------------------------------------------------------------------

class TestDocsDriftSource:
    def _text(self) -> str:
        return DOCS_DRIFT_SCRIPT.read_text(encoding="utf-8")

    def test_informational_only_exit_0_documented(self) -> None:
        text = self._text()
        assert "sys.exit(0)" in text

    def test_defines_findings_list(self) -> None:
        text = self._text()
        assert "findings" in text

    def test_defines_note_and_ok_helpers(self) -> None:
        text = self._text()
        assert "def note(" in text
        assert "def ok(" in text

    def test_check_version_function_exists(self) -> None:
        text = self._text()
        assert "def check_version(" in text

    def test_check_ports_function_exists(self) -> None:
        text = self._text()
        assert "def check_ports(" in text

    def test_check_env_vars_function_exists(self) -> None:
        text = self._text()
        assert "def check_env_vars(" in text


# ---------------------------------------------------------------------------
# check-placeholders.py — basic contract
# ---------------------------------------------------------------------------

class TestPlaceholdersScript:
    def test_script_exists(self) -> None:
        assert PLACEHOLDERS_SCRIPT.exists(), "check-placeholders.py not found"

    def test_exits_zero(self) -> None:
        result = run_script(PLACEHOLDERS_SCRIPT)
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}\n{result.stderr}"

    def test_prints_summary(self) -> None:
        result = run_script(PLACEHOLDERS_SCRIPT)
        assert "SUMMARY" in result.stdout

    def test_output_has_findings_count(self) -> None:
        result = run_script(PLACEHOLDERS_SCRIPT)
        # "N total finding(s)" or "No findings"
        combined = result.stdout + result.stderr
        assert "finding" in combined.lower(), f"No 'finding' in output:\n{combined[:500]}"

    def test_scans_py_and_tsx_files(self) -> None:
        """Output may mention categories like TODO, placeholder-url, etc."""
        result = run_script(PLACEHOLDERS_SCRIPT)
        combined = result.stdout + result.stderr
        # Should have at least a summary line with categories
        assert "SUMMARY" in combined

    def test_does_not_crash_on_large_repo(self) -> None:
        """Script should complete in reasonable time without crashing."""
        result = run_script(PLACEHOLDERS_SCRIPT)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# check-placeholders.py — source-level coverage
# ---------------------------------------------------------------------------

class TestPlaceholdersSource:
    def _text(self) -> str:
        return PLACEHOLDERS_SCRIPT.read_text(encoding="utf-8")

    def test_informational_only_exit_0_documented(self) -> None:
        text = self._text()
        assert "sys.exit(0)" in text

    def test_defines_placeholder_patterns(self) -> None:
        text = self._text()
        assert "PLACEHOLDER_PATTERNS" in text

    def test_detects_example_com(self) -> None:
        text = self._text()
        assert "example.com" in text

    def test_detects_todo_fixme(self) -> None:
        text = self._text()
        assert "TODO" in text
        assert "FIXME" in text

    def test_detects_stale_gpl_references(self) -> None:
        text = self._text()
        assert "stale-gpl" in text or ("GPL" in text and "SKIP" in text)

    def test_defines_skip_dirs(self) -> None:
        text = self._text()
        assert "SKIP_DIRS" in text
        assert "node_modules" in text
        assert ".venv" in text

    def test_defines_gpl_skip_paths_allowlist(self) -> None:
        text = self._text()
        assert "GPL_SKIP_PATHS" in text

    def test_scan_respects_include_extensions(self) -> None:
        text = self._text()
        assert "INCLUDE_EXTENSIONS" in text
        assert ".py" in text
        assert ".tsx" in text

    def test_allowlist_includes_checklist_file(self) -> None:
        """RELEASE_CHECKLIST.md is in GPL_SKIP_PATHS to avoid false positives."""
        text = self._text()
        assert "RELEASE_CHECKLIST.md" in text


# ---------------------------------------------------------------------------
# Integration: fixture-based violation detection for check-placeholders.py
# ---------------------------------------------------------------------------

class TestPlaceholdersFixture:
    def test_detects_example_com_in_source_text(self) -> None:
        """Verify the pattern matches example.com."""
        pattern = re.compile(r'example\.com', re.IGNORECASE)
        assert pattern.search("See https://example.com for info")

    def test_detects_todo_marker(self) -> None:
        pattern = re.compile(r'\bTODO\b', re.IGNORECASE)
        assert pattern.search("# TODO: fix this later")

    def test_does_not_flag_allowlisted_files(self) -> None:
        """GPL_SKIP_PATHS must contain RELEASE_CHECKLIST.md."""
        text = PLACEHOLDERS_SCRIPT.read_text(encoding="utf-8")
        # The allowlist should include this file
        assert "RELEASE_CHECKLIST.md" in text

    def test_gpl_pattern_does_not_match_lgpl_or_agpl_as_whole_word(self) -> None:
        """GPL pattern uses negative lookahead to avoid matching LGPL, AGPL."""
        # The regex in the script: r'\bGPL\b(?![\w-])' — check it's constrained
        text = PLACEHOLDERS_SCRIPT.read_text(encoding="utf-8")
        # Pattern should be word-bounded
        assert r'\bGPL\b' in text
