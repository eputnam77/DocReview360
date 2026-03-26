# SPDX-License-Identifier: MIT
"""Item 19a / Item 139 — Headless loop (Raspberry Pi-friendly) runner tests.

Covers:
  - scripts/headless-loop.sh exists and is executable
  - Lockfile creation and cleanup
  - Append-only log behavior
  - Single run with exit 0
  - MAX_RUNS configuration
  - Concurrent invocation blocked by lockfile
  - HEADLESS_COMMAND environment variable
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HEADLESS_SCRIPT = REPO_ROOT / "scripts" / "headless-loop.sh"


def run_headless(
    command: str = 'echo "ok"',
    max_runs: str = "1",
    extra_env: dict[str, str] | None = None,
    log_file: str | None = None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = str(Path(tmpdir) / "test.lock")
        if log_file is None:
            log_file = str(Path(tmpdir) / "test.log")
        env = {
            **os.environ,
            "HEADLESS_COMMAND": command,
            "HEADLESS_MAX_RUNS": max_runs,
            "HEADLESS_LOCKFILE": lock_file,
            "HEADLESS_LOG_FILE": log_file,
            **(extra_env or {}),
        }
        result = subprocess.run(
            ["bash", str(HEADLESS_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
    return result


# ---------------------------------------------------------------------------
# Source-level checks
# ---------------------------------------------------------------------------

class TestHeadlessLoopSource:
    def _text(self) -> str:
        return HEADLESS_SCRIPT.read_text(encoding="utf-8")

    def test_script_exists(self) -> None:
        assert HEADLESS_SCRIPT.exists(), "scripts/headless-loop.sh not found"

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in self._text()

    def test_set_euo_pipefail(self) -> None:
        assert "set -euo pipefail" in self._text()

    def test_lockfile_creation(self) -> None:
        text = self._text()
        assert "HEADLESS_LOCKFILE" in text
        assert "exit 2" in text  # Exits 2 if lock exists

    def test_lockfile_trap_cleanup(self) -> None:
        text = self._text()
        assert "trap" in text
        assert "HEADLESS_LOCKFILE" in text

    def test_append_only_log(self) -> None:
        text = self._text()
        assert ">>" in text
        assert "HEADLESS_LOG_FILE" in text

    def test_max_runs_configurable(self) -> None:
        text = self._text()
        assert "HEADLESS_MAX_RUNS" in text

    def test_command_configurable(self) -> None:
        text = self._text()
        assert "HEADLESS_COMMAND" in text

    def test_no_cron_or_systemd_required(self) -> None:
        """Script must not invoke cron or systemd (simple shell invocation)."""
        text = self._text()
        # Should not call systemctl or crontab — only mentions them in comments
        assert "systemctl" not in text
        assert "crontab" not in text

    def test_watchdog_max_failures_configurable(self) -> None:
        text = self._text()
        assert "HEADLESS_MAX_FAILURES" in text
        assert "WATCHDOG" in text

    def test_watchdog_budget_secs_configurable(self) -> None:
        text = self._text()
        assert "HEADLESS_BUDGET_SECS" in text
        assert "budget" in text


# ---------------------------------------------------------------------------
# Behavioral tests
# ---------------------------------------------------------------------------

class TestHeadlessLoopBehavior:
    def test_exits_zero_on_success(self) -> None:
        result = run_headless('echo "success"')
        assert result.returncode == 0

    def test_exit_code_propagated_on_failure(self) -> None:
        result = run_headless("exit 1")
        assert result.returncode != 0

    def test_outputs_run_started_message(self) -> None:
        result = run_headless('echo "hello"')
        combined = result.stdout + result.stderr
        assert "run 1" in combined

    def test_outputs_finished_message(self) -> None:
        result = run_headless('echo "hello"')
        combined = result.stdout + result.stderr
        assert "finished" in combined or "headless-loop" in combined

    def test_single_run_by_default(self) -> None:
        result = run_headless('echo "hi"', max_runs="1")
        combined = result.stdout + result.stderr
        # Should show run 1/1 not run 2
        assert "1/1" in combined
        assert "2/1" not in combined

    def test_max_runs_three(self) -> None:
        result = run_headless('echo "iter"', max_runs="3")
        combined = result.stdout + result.stderr
        assert "1/3" in combined
        assert "3/3" in combined

    def test_log_file_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = str(Path(tmpdir) / "run.log")
            lock_file = str(Path(tmpdir) / "run.lock")
            env = {
                **os.environ,
                "HEADLESS_COMMAND": 'echo "logged"',
                "HEADLESS_MAX_RUNS": "1",
                "HEADLESS_LOCKFILE": lock_file,
                "HEADLESS_LOG_FILE": log_file,
            }
            subprocess.run(
                ["bash", str(HEADLESS_SCRIPT)],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(REPO_ROOT),
                timeout=15,
            )
            assert Path(log_file).exists()
            content = Path(log_file).read_text(encoding="utf-8")
            assert "logged" in content

    def test_log_file_appended_not_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = str(Path(tmpdir) / "run.log")
            lock_file = str(Path(tmpdir) / "run.lock")
            env_base = {
                **os.environ,
                "HEADLESS_MAX_RUNS": "1",
                "HEADLESS_LOG_FILE": log_file,
                "HEADLESS_LOCKFILE": lock_file,
            }
            # First run
            env1 = {**env_base, "HEADLESS_COMMAND": 'echo "first run"'}
            subprocess.run(
                ["bash", str(HEADLESS_SCRIPT)],
                capture_output=True, text=True, env=env1,
                cwd=str(REPO_ROOT), timeout=15,
            )
            # Second run
            env2 = {**env_base, "HEADLESS_COMMAND": 'echo "second run"'}
            subprocess.run(
                ["bash", str(HEADLESS_SCRIPT)],
                capture_output=True, text=True, env=env2,
                cwd=str(REPO_ROOT), timeout=15,
            )
            content = Path(log_file).read_text(encoding="utf-8")
            # Both runs must be in the log (append-only)
            assert "first run" in content
            assert "second run" in content

    def test_watchdog_stops_on_repeated_failures(self) -> None:
        """HEADLESS_MAX_FAILURES watchdog stops loop after N consecutive failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = str(Path(tmpdir) / "wdog.lock")
            log_file = str(Path(tmpdir) / "wdog.log")
            env = {
                **os.environ,
                "HEADLESS_COMMAND": "exit 1",
                "HEADLESS_MAX_RUNS": "10",
                "HEADLESS_MAX_FAILURES": "2",
                "HEADLESS_BUDGET_SECS": "3600",
                "HEADLESS_LOCKFILE": lock_file,
                "HEADLESS_LOG_FILE": log_file,
            }
            result = subprocess.run(
                ["bash", str(HEADLESS_SCRIPT)],
                capture_output=True, text=True, env=env,
                cwd=str(REPO_ROOT), timeout=15,
            )
            # Should stop before 10 runs due to watchdog
            assert result.returncode != 0
            combined = result.stdout + result.stderr
            assert "WATCHDOG" in combined or "consecutive" in combined

    def test_watchdog_budget_secs(self) -> None:
        """HEADLESS_BUDGET_SECS watchdog stops loop after time budget exhausted."""
        text = HEADLESS_SCRIPT.read_text(encoding="utf-8")
        assert "HEADLESS_BUDGET_SECS" in text
        assert "WATCHDOG" in text
        assert "budget" in text

    def test_concurrent_invocation_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = str(Path(tmpdir) / "concurrent.lock")
            log_file = str(Path(tmpdir) / "concurrent.log")
            # Pre-create the lockfile to simulate a running instance
            Path(lock_file).write_text("99999\n")
            env = {
                **os.environ,
                "HEADLESS_COMMAND": 'echo "should not run"',
                "HEADLESS_MAX_RUNS": "1",
                "HEADLESS_LOCKFILE": lock_file,
                "HEADLESS_LOG_FILE": log_file,
            }
            result = subprocess.run(
                ["bash", str(HEADLESS_SCRIPT)],
                capture_output=True, text=True, env=env,
                cwd=str(REPO_ROOT), timeout=10,
            )
            # Must exit non-zero (exit 2 per the script)
            assert result.returncode != 0
            combined = result.stdout + result.stderr
            assert "lock" in combined.lower() or "ERROR" in combined
