# SPDX-License-Identifier: MIT
"""Items 163, 164, 221 — Triage, flaky-test hunter, and issue-grooming tests.

Covers:
  - scripts/failing-test-triage.py  (Item 163)
  - scripts/flaky-test-hunter.py    (Item 164)
  - scripts/issue-grooming-loop.py  (Item 221)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

TRIAGE_SCRIPT = SCRIPTS_DIR / "failing-test-triage.py"
FLAKY_SCRIPT = SCRIPTS_DIR / "flaky-test-hunter.py"
GROOMING_SCRIPT = SCRIPTS_DIR / "issue-grooming-loop.py"


def run_script(path: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path), *(extra_args or [])],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


# ===========================================================================
# Failing-test triage (Item 163)
# ===========================================================================

class TestFailingTestTriage:
    def test_script_exists(self) -> None:
        assert TRIAGE_SCRIPT.exists()

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in TRIAGE_SCRIPT.read_text(encoding="utf-8")

    def test_exits_zero_skip_run(self) -> None:
        result = run_script(TRIAGE_SCRIPT, ["--skip-run"])
        assert result.returncode == 0

    def test_prints_summary(self) -> None:
        result = run_script(TRIAGE_SCRIPT, ["--skip-run"])
        assert "SUMMARY" in result.stdout

    def test_skip_run_flag(self) -> None:
        result = run_script(TRIAGE_SCRIPT, ["--skip-run"])
        combined = result.stdout + result.stderr
        assert "skip" in combined.lower()

    def test_parse_failures_function(self) -> None:
        assert "parse_failures" in TRIAGE_SCRIPT.read_text(encoding="utf-8")

    def test_cluster_failures_function(self) -> None:
        assert "cluster_failures" in TRIAGE_SCRIPT.read_text(encoding="utf-8")

    def test_infer_root_cause_function(self) -> None:
        assert "_infer_root_cause" in TRIAGE_SCRIPT.read_text(encoding="utf-8")

    def test_suggest_action_function(self) -> None:
        assert "_suggest_action" in TRIAGE_SCRIPT.read_text(encoding="utf-8")

    def test_write_report_function(self) -> None:
        assert "write_report" in TRIAGE_SCRIPT.read_text(encoding="utf-8")

    def test_json_report_flag_accepted(self, tmp_path: Path) -> None:
        out = str(tmp_path / "triage.json")
        result = run_script(TRIAGE_SCRIPT, ["--skip-run", "--json-report", out])
        assert result.returncode == 0

    def test_exit_zero_documented(self) -> None:
        assert "sys.exit(0)" in TRIAGE_SCRIPT.read_text(encoding="utf-8")

    def test_assertionerror_root_cause(self) -> None:
        text = TRIAGE_SCRIPT.read_text(encoding="utf-8")
        assert "AssertionError" in text or "assertionerror" in text.lower()

    def test_importerror_root_cause(self) -> None:
        text = TRIAGE_SCRIPT.read_text(encoding="utf-8")
        assert "ImportError" in text or "importerror" in text.lower()

    def test_severity_ordering(self) -> None:
        text = TRIAGE_SCRIPT.read_text(encoding="utf-8")
        ci = text.find('"CRITICAL"')
        hi = text.find('"HIGH"')
        if ci >= 0 and hi >= 0:
            assert ci < hi


# ===========================================================================
# Flaky-test hunter (Item 164)
# ===========================================================================

class TestFlakyTestHunter:
    def test_script_exists(self) -> None:
        assert FLAKY_SCRIPT.exists()

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in FLAKY_SCRIPT.read_text(encoding="utf-8")

    def test_exits_zero_single_fast_test(self) -> None:
        # Run a single fast test 1 time to stay fast
        result = run_script(
            FLAKY_SCRIPT,
            ["--runs", "1", "--test-path", "tests/test_item19a_scripts.py"],
        )
        assert result.returncode == 0, result.stderr[:300]

    def test_prints_summary(self) -> None:
        result = run_script(
            FLAKY_SCRIPT,
            ["--runs", "1", "--test-path", "tests/test_item19a_scripts.py"],
        )
        assert "SUMMARY" in result.stdout

    def test_hunt_flaky_function(self) -> None:
        assert "hunt_flaky" in FLAKY_SCRIPT.read_text(encoding="utf-8")

    def test_rank_by_frequency_function(self) -> None:
        assert "rank_by_frequency" in FLAKY_SCRIPT.read_text(encoding="utf-8")

    def test_find_first_bad_commit_function(self) -> None:
        assert "find_first_bad_commit" in FLAKY_SCRIPT.read_text(encoding="utf-8")

    def test_write_report_function(self) -> None:
        assert "write_report" in FLAKY_SCRIPT.read_text(encoding="utf-8")

    def test_runs_flag(self) -> None:
        text = FLAKY_SCRIPT.read_text(encoding="utf-8")
        assert "--runs" in text or '"runs"' in text

    def test_report_flag_accepted(self, tmp_path: Path) -> None:
        out = str(tmp_path / "flaky.md")
        result = run_script(
            FLAKY_SCRIPT,
            ["--runs", "1", "--test-path", "tests/test_item19a_scripts.py", "--report", out],
        )
        assert result.returncode == 0

    def test_exit_zero_documented(self) -> None:
        assert "sys.exit(0)" in FLAKY_SCRIPT.read_text(encoding="utf-8")

    def test_consistently_failing_label(self) -> None:
        assert "CONSISTENTLY" in FLAKY_SCRIPT.read_text(encoding="utf-8")

    def test_flaky_label(self) -> None:
        text = FLAKY_SCRIPT.read_text(encoding="utf-8")
        assert "FLAKY" in text or "flaky" in text.lower()

    def test_git_log_for_first_bad_commit(self) -> None:
        text = FLAKY_SCRIPT.read_text(encoding="utf-8")
        assert "git" in text and "log" in text


# ===========================================================================
# Issue grooming loop (Item 221)
# ===========================================================================

class TestIssueGroomingLoop:
    def test_script_exists(self) -> None:
        assert GROOMING_SCRIPT.exists()

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in GROOMING_SCRIPT.read_text(encoding="utf-8")

    def test_exits_zero(self) -> None:
        result = run_script(GROOMING_SCRIPT, ["--sources", "git"])
        assert result.returncode == 0, result.stderr[:300]

    def test_prints_summary(self) -> None:
        result = run_script(GROOMING_SCRIPT, ["--sources", "git"])
        assert "SUMMARY" in result.stdout

    def test_collect_from_triage_function(self) -> None:
        assert "collect_from_triage" in GROOMING_SCRIPT.read_text(encoding="utf-8")

    def test_collect_from_bandit_function(self) -> None:
        assert "collect_from_bandit" in GROOMING_SCRIPT.read_text(encoding="utf-8")

    def test_collect_from_precommit_function(self) -> None:
        assert "collect_from_precommit" in GROOMING_SCRIPT.read_text(encoding="utf-8")

    def test_deduplicate_function(self) -> None:
        assert "deduplicate" in GROOMING_SCRIPT.read_text(encoding="utf-8")

    def test_write_output_function(self) -> None:
        assert "write_output" in GROOMING_SCRIPT.read_text(encoding="utf-8")

    def test_sources_flag(self) -> None:
        text = GROOMING_SCRIPT.read_text(encoding="utf-8")
        assert "--sources" in text

    def test_sources_all_accepted(self) -> None:
        result = run_script(GROOMING_SCRIPT, ["--sources", "all"])
        assert result.returncode == 0

    def test_output_flag_accepted(self, tmp_path: Path) -> None:
        out = str(tmp_path / "issues.md")
        result = run_script(GROOMING_SCRIPT, ["--sources", "git", "--output", out])
        assert result.returncode == 0

    def test_no_auto_github_creation(self) -> None:
        text = GROOMING_SCRIPT.read_text(encoding="utf-8")
        # Must NOT call gh issue create or requests.post to github
        assert "gh issue create" not in text
        assert "api.github.com/repos" not in text

    def test_human_review_required_note(self) -> None:
        text = GROOMING_SCRIPT.read_text(encoding="utf-8")
        assert "human review" in text.lower() or "manually" in text.lower()

    def test_exit_zero_documented(self) -> None:
        assert "sys.exit(0)" in GROOMING_SCRIPT.read_text(encoding="utf-8")

    def test_severity_dedup(self) -> None:
        text = GROOMING_SCRIPT.read_text(encoding="utf-8")
        assert "CRITICAL" in text and "HIGH" in text and "MEDIUM" in text
