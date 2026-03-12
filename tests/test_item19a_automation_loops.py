# SPDX-License-Identifier: MIT
"""Items 190–195 — Automation loop scripts tests.

Covers source-level and contract tests for:
  - scripts/performance-regression-check.py (Item 190)
  - scripts/ux-smoke-review.py              (Item 192)
  - scripts/audit-log-integrity-check.py   (Item 193)
  - scripts/ml-packaging-verifier.py       (Item 194)
  - scripts/release-note-drafter.py        (Item 195)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

PERF_SCRIPT = SCRIPTS_DIR / "performance-regression-check.py"
UX_SCRIPT = SCRIPTS_DIR / "ux-smoke-review.py"
AUDIT_SCRIPT = SCRIPTS_DIR / "audit-log-integrity-check.py"
ML_SCRIPT = SCRIPTS_DIR / "ml-packaging-verifier.py"
NOTES_SCRIPT = SCRIPTS_DIR / "release-note-drafter.py"


def run_script(path: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path), *(extra_args or [])],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


# ===========================================================================
# Performance regression check (Item 190)
# ===========================================================================

class TestPerfRegressionExists:
    def test_script_exists(self) -> None:
        assert PERF_SCRIPT.exists()

    def test_exits_zero(self) -> None:
        result = run_script(PERF_SCRIPT)
        assert result.returncode == 0, result.stderr[:200]

    def test_prints_summary(self) -> None:
        result = run_script(PERF_SCRIPT)
        assert "SUMMARY" in result.stdout

    def test_covers_baseline_doc(self) -> None:
        result = run_script(PERF_SCRIPT)
        combined = result.stdout + result.stderr
        assert "baseline" in combined.lower() or "threshold" in combined.lower()

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in PERF_SCRIPT.read_text(encoding="utf-8")

    def test_threshold_flag(self) -> None:
        result = run_script(PERF_SCRIPT, ["--threshold", "0.3"])
        assert result.returncode == 0

    def test_check_baseline_doc_function(self) -> None:
        assert "check_baseline_doc" in PERF_SCRIPT.read_text(encoding="utf-8")

    def test_compare_metrics_function(self) -> None:
        assert "compare_metrics" in PERF_SCRIPT.read_text(encoding="utf-8")

    def test_print_summary_function(self) -> None:
        assert "print_summary" in PERF_SCRIPT.read_text(encoding="utf-8")

    def test_severity_ordering(self) -> None:
        text = PERF_SCRIPT.read_text(encoding="utf-8")
        ci = text.find('"CRITICAL"')
        hi = text.find('"HIGH"')
        if ci >= 0 and hi >= 0:
            assert ci < hi

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in PERF_SCRIPT.read_text(encoding="utf-8")


# ===========================================================================
# UX smoke review (Item 192)
# ===========================================================================

class TestUXSmokeReviewExists:
    def test_script_exists(self) -> None:
        assert UX_SCRIPT.exists()

    def test_exits_zero(self) -> None:
        result = run_script(UX_SCRIPT)
        assert result.returncode == 0, result.stderr[:200]

    def test_prints_summary(self) -> None:
        result = run_script(UX_SCRIPT)
        assert "SUMMARY" in result.stdout

    def test_source_level_checks_run(self) -> None:
        result = run_script(UX_SCRIPT)
        combined = result.stdout + result.stderr
        assert "source" in combined.lower() or "demo" in combined.lower() or "alice" in combined.lower()

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in UX_SCRIPT.read_text(encoding="utf-8")

    def test_check_auth_flow_function(self) -> None:
        assert "check_auth_flow" in UX_SCRIPT.read_text(encoding="utf-8")

    def test_check_health_endpoints_function(self) -> None:
        assert "check_health_endpoints" in UX_SCRIPT.read_text(encoding="utf-8")

    def test_check_error_handling_function(self) -> None:
        assert "check_error_handling" in UX_SCRIPT.read_text(encoding="utf-8")

    def test_check_source_level_function(self) -> None:
        assert "check_source_level" in UX_SCRIPT.read_text(encoding="utf-8")

    def test_alice_and_bob_referenced(self) -> None:
        text = UX_SCRIPT.read_text(encoding="utf-8")
        assert "alice" in text and "bob" in text

    def test_use_test_client_flag(self) -> None:
        result = run_script(UX_SCRIPT, ["--use-test-client"])
        assert result.returncode == 0, result.stderr[:300]

    def test_test_client_runs_runtime_checks(self) -> None:
        result = run_script(UX_SCRIPT, ["--use-test-client"])
        combined = result.stdout + result.stderr
        assert "health" in combined.lower() or "auth" in combined.lower() or "401" in combined

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in UX_SCRIPT.read_text(encoding="utf-8")


# ===========================================================================
# Audit log integrity check (Item 193)
# ===========================================================================

class TestAuditLogIntegrityExists:
    def test_script_exists(self) -> None:
        assert AUDIT_SCRIPT.exists()

    def test_exits_zero(self) -> None:
        result = run_script(AUDIT_SCRIPT)
        assert result.returncode == 0, result.stderr[:200]

    def test_prints_summary(self) -> None:
        result = run_script(AUDIT_SCRIPT)
        assert "SUMMARY" in result.stdout

    def test_covers_hash_chain(self) -> None:
        result = run_script(AUDIT_SCRIPT)
        combined = result.stdout + result.stderr
        assert "hash" in combined.lower() or "chain" in combined.lower()

    def test_covers_append_only(self) -> None:
        result = run_script(AUDIT_SCRIPT)
        combined = result.stdout + result.stderr
        assert "append" in combined.lower() or "immutable" in combined.lower()

    def test_covers_retention(self) -> None:
        result = run_script(AUDIT_SCRIPT)
        combined = result.stdout + result.stderr
        assert "retention" in combined.lower()

    def test_covers_backup(self) -> None:
        result = run_script(AUDIT_SCRIPT)
        combined = result.stdout + result.stderr
        assert "backup" in combined.lower() or "restore" in combined.lower()

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in AUDIT_SCRIPT.read_text(encoding="utf-8")

    def test_check_log_package_function(self) -> None:
        assert "check_log_package_structure" in AUDIT_SCRIPT.read_text(encoding="utf-8")

    def test_check_hash_chain_function(self) -> None:
        assert "check_hash_chain" in AUDIT_SCRIPT.read_text(encoding="utf-8")

    def test_check_append_only_function(self) -> None:
        assert "check_append_only" in AUDIT_SCRIPT.read_text(encoding="utf-8")

    def test_check_backup_restore_function(self) -> None:
        assert "check_backup_restore" in AUDIT_SCRIPT.read_text(encoding="utf-8")

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in AUDIT_SCRIPT.read_text(encoding="utf-8")

    def test_verify_audit_log_chain_referenced(self) -> None:
        assert "verify_audit_log_chain" in AUDIT_SCRIPT.read_text(encoding="utf-8")


# ===========================================================================
# ML packaging verifier (Item 194)
# ===========================================================================

class TestMLPackagingVerifierExists:
    def test_script_exists(self) -> None:
        assert ML_SCRIPT.exists()

    def test_exits_zero(self) -> None:
        result = run_script(ML_SCRIPT)
        assert result.returncode == 0, result.stderr[:200]

    def test_prints_summary(self) -> None:
        result = run_script(ML_SCRIPT)
        assert "SUMMARY" in result.stdout

    def test_covers_model_metadata(self) -> None:
        result = run_script(ML_SCRIPT)
        combined = result.stdout + result.stderr
        assert "metadata" in combined.lower()

    def test_covers_onnx(self) -> None:
        result = run_script(ML_SCRIPT)
        combined = result.stdout + result.stderr
        assert "onnx" in combined.lower()

    def test_covers_golden_fixtures(self) -> None:
        result = run_script(ML_SCRIPT)
        combined = result.stdout + result.stderr
        assert "golden" in combined.lower() or "fixture" in combined.lower() or "drift" in combined.lower()

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in ML_SCRIPT.read_text(encoding="utf-8")

    def test_drift_threshold_flag(self) -> None:
        result = run_script(ML_SCRIPT, ["--drift-threshold", "0.05"])
        assert result.returncode == 0

    def test_check_ml_structure_function(self) -> None:
        assert "check_ml_package_structure" in ML_SCRIPT.read_text(encoding="utf-8")

    def test_check_model_metadata_function(self) -> None:
        assert "check_model_metadata" in ML_SCRIPT.read_text(encoding="utf-8")

    def test_check_drift_function(self) -> None:
        assert "check_golden_fixture_drift" in ML_SCRIPT.read_text(encoding="utf-8")

    def test_check_onnx_pytorch_function(self) -> None:
        assert "check_onnx_pytorch_parity" in ML_SCRIPT.read_text(encoding="utf-8")

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in ML_SCRIPT.read_text(encoding="utf-8")


# ===========================================================================
# Release-note drafter (Item 195)
# ===========================================================================

class TestReleaseNoteDrafterExists:
    def test_script_exists(self) -> None:
        assert NOTES_SCRIPT.exists()

    def test_exits_zero(self) -> None:
        result = run_script(NOTES_SCRIPT)
        assert result.returncode == 0, result.stderr[:200]

    def test_prints_summary(self) -> None:
        result = run_script(NOTES_SCRIPT)
        assert "SUMMARY" in result.stdout

    def test_drafts_release_notes(self) -> None:
        result = run_script(NOTES_SCRIPT)
        combined = result.stdout + result.stderr
        assert "draft" in combined.lower() or "release" in combined.lower() or "changelog" in combined.lower()

    def test_covers_commits(self) -> None:
        result = run_script(NOTES_SCRIPT)
        combined = result.stdout + result.stderr
        assert "commit" in combined.lower()

    def test_covers_changelog(self) -> None:
        result = run_script(NOTES_SCRIPT)
        combined = result.stdout + result.stderr
        assert "changelog" in combined.lower() or "CHANGELOG" in combined

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in NOTES_SCRIPT.read_text(encoding="utf-8")

    def test_since_flag(self) -> None:
        result = run_script(NOTES_SCRIPT, ["--since", "HEAD~5"])
        assert result.returncode == 0

    def test_output_flag(self, tmp_path: Path) -> None:
        out = str(tmp_path / "draft.md")
        result = run_script(NOTES_SCRIPT, ["--output", out])
        assert result.returncode == 0
        assert Path(out).exists()
        content = Path(out).read_text(encoding="utf-8")
        assert "Draft" in content or "Release" in content

    def test_collect_commits_function(self) -> None:
        assert "collect_commits" in NOTES_SCRIPT.read_text(encoding="utf-8")

    def test_categorize_commits_function(self) -> None:
        assert "categorize_commits" in NOTES_SCRIPT.read_text(encoding="utf-8")

    def test_draft_release_notes_function(self) -> None:
        assert "draft_release_notes" in NOTES_SCRIPT.read_text(encoding="utf-8")

    def test_check_changelog_function(self) -> None:
        assert "check_changelog" in NOTES_SCRIPT.read_text(encoding="utf-8")

    def test_conventional_commit_categories(self) -> None:
        text = NOTES_SCRIPT.read_text(encoding="utf-8")
        assert "feat" in text and "fix" in text and "docs" in text

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in NOTES_SCRIPT.read_text(encoding="utf-8")
