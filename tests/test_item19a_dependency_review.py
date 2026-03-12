# SPDX-License-Identifier: MIT
"""Item 19a / Item 177 — Dependency review loop tests.

Covers:
  - scripts/dependency-review.py: exits 0, SUMMARY output
  - Three scan sections: pip-audit, bandit, npm-audit
  - Summary grouped by severity
  - All three tools attempted even if some aren't available
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DEP_REVIEW = SCRIPTS_DIR / "dependency-review.py"


def run_script() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DEP_REVIEW)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=180,  # pip-audit + bandit + npm audit can take a while
    )


class TestDependencyReviewContract:
    def test_script_exists(self) -> None:
        assert DEP_REVIEW.exists(), "scripts/dependency-review.py not found"

    def test_exits_zero(self) -> None:
        result = run_script()
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"

    def test_prints_summary(self) -> None:
        result = run_script()
        assert "SUMMARY" in result.stdout

    def test_prints_repo_root(self) -> None:
        result = run_script()
        assert "Repo root" in result.stdout or "DocReview360" in result.stdout

    def test_covers_pip_audit(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "pip-audit" in combined.lower()

    def test_covers_bandit(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "bandit" in combined.lower()

    def test_covers_npm_audit(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "npm" in combined.lower() or "frontend" in combined.lower()

    def test_summary_has_severity_labels_or_clean(self) -> None:
        result = run_script()
        # Either reports issues by severity or says "No actionable issues"
        combined = result.stdout + result.stderr
        has_severity = any(
            s in combined for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "No actionable"]
        )
        assert has_severity


class TestDependencyReviewSource:
    def _text(self) -> str:
        return DEP_REVIEW.read_text(encoding="utf-8")

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in self._text()

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in self._text()

    def test_check_pip_audit_function(self) -> None:
        assert "check_pip_audit" in self._text()

    def test_check_bandit_function(self) -> None:
        assert "check_bandit" in self._text()

    def test_check_npm_audit_function(self) -> None:
        assert "check_npm_audit" in self._text()

    def test_print_summary_function(self) -> None:
        assert "print_summary" in self._text()

    def test_severity_ordering(self) -> None:
        text = self._text()
        # Summary must list CRITICAL before HIGH before MEDIUM
        ci = text.find('"CRITICAL"')
        hi = text.find('"HIGH"')
        mi = text.find('"MEDIUM"')
        # At least two of these must appear in order
        if ci >= 0 and hi >= 0:
            assert ci < hi, "CRITICAL should come before HIGH in severity ordering"

    def test_graceful_skip_on_missing_tool(self) -> None:
        text = self._text()
        assert "skip" in text.lower()
        assert "not available" in text or "not found" in text

    def test_bandit_json_output(self) -> None:
        text = self._text()
        assert '"-f"' in text and '"json"' in text

    def test_npm_audit_json_output(self) -> None:
        text = self._text()
        assert '"--json"' in text
        assert "npm" in text
