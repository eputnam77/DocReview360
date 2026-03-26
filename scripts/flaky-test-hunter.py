#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Flaky-test hunter.

Reruns smoke tests multiple times, captures artifacts, and ranks failures
by frequency. Also checks git history for first bad commit.
Always exits 0 (informational).

Usage:
    python scripts/flaky-test-hunter.py
    python scripts/flaky-test-hunter.py --runs 5 --test-path tests/test_approvals.py
    python scripts/flaky-test-hunter.py --runs 3 --report artifacts/flaky.md
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "flaky"

findings: list[dict[str, str]] = []


def note(category: str, severity: str, message: str) -> None:
    findings.append({"category": category, "severity": severity, "message": message})
    indicator = "!" if severity in ("CRITICAL", "HIGH") else "~"
    print(f"  [{indicator}] [{category}] {severity}: {message}")


def ok(category: str, message: str) -> None:
    print(f"  [+] [{category}] ok: {message}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


FAILED_RE = re.compile(r"FAILED\s+([\w/.:\[\]-]+)")


def _run_once(test_path: str | None, run_num: int) -> tuple[int, list[str]]:
    """Run pytest once and return (returncode, list of failed test IDs)."""
    cmd = [
        sys.executable, "-m", "pytest",
        "--tb=no", "-q",
        "--ignore=_debug_test.py",
        "--ignore=tests/test_auth_repository.py",
        "--no-header",
    ]
    if test_path:
        cmd.append(test_path)
    else:
        cmd += ["tests/", "-x", "--maxfail=10"]

    env = {**os.environ, "DOCREVIEW360_ENV": "dev"}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=180,
            env=env,
        )
        combined = result.stdout + result.stderr
        failed = [m.group(1) for m in FAILED_RE.finditer(combined)]
        status = "PASS" if result.returncode == 0 else f"FAIL ({len(failed)})"
        print(f"    run {run_num}: {status}")
        return result.returncode, failed
    except subprocess.TimeoutExpired:
        print(f"    run {run_num}: TIMEOUT")
        return -1, ["<timeout>"]


def hunt_flaky(runs: int, test_path: str | None) -> dict[str, list[int]]:
    """Run tests `runs` times and collect per-test failure run indices."""
    section(f"Flaky Test Hunt ({runs} run(s))")

    per_test_failures: dict[str, list[int]] = {}
    all_pass = True

    for i in range(1, runs + 1):
        rc, failed = _run_once(test_path, i)
        if rc != 0:
            all_pass = False
        for test_id in failed:
            per_test_failures.setdefault(test_id, []).append(i)

    if all_pass:
        ok("Hunt", f"All {runs} run(s) passed — no flakiness detected")
    elif per_test_failures:
        note(
            "Hunt",
            "MEDIUM",
            f"{len(per_test_failures)} distinct test(s) failed across {runs} run(s)",
        )
    else:
        note("Hunt", "LOW", "Some run(s) failed but no test IDs captured — check pytest output")

    return per_test_failures


def rank_by_frequency(
    per_test_failures: dict[str, list[int]],
    runs: int,
) -> list[dict[str, object]]:
    """Rank tests by failure frequency, classify as flaky vs consistently failing."""
    section("Ranking by Failure Frequency")

    ranked = []
    for test_id, fail_runs in sorted(
        per_test_failures.items(), key=lambda x: -len(x[1])
    ):
        freq = len(fail_runs) / runs
        if freq >= 0.9:
            label = "CONSISTENTLY FAILING"
            severity = "HIGH"
        elif freq >= 0.3:
            label = "FLAKY (intermittent)"
            severity = "MEDIUM"
        else:
            label = "OCCASIONALLY FLAKY"
            severity = "LOW"

        entry = {
            "test_id": test_id,
            "failures": len(fail_runs),
            "runs": runs,
            "frequency": freq,
            "label": label,
            "fail_runs": fail_runs,
        }
        ranked.append(entry)
        note("Rank", severity, f"{test_id}: {len(fail_runs)}/{runs} ({label})")

    return ranked


def find_first_bad_commit(test_id: str) -> str | None:
    """Attempt git log to find when this test file was last changed."""
    # Extract file path from test_id
    m = re.match(r"(tests/[\w/.]+\.py)", test_id)
    if not m:
        return None

    test_file = m.group(1)
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5", "--", test_file],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def write_report(
    ranked: list[dict[str, object]],
    runs: int,
    report_path: Path | None,
) -> None:
    section("Flaky Test Report")

    if not ranked:
        ok("Report", "No flaky tests detected")
        return

    lines = [
        "# Flaky Test Report",
        "",
        f"Total runs: {runs}",
        f"Flaky/failing tests found: {len(ranked)}",
        "",
        "| Test | Failures | Frequency | Classification |",
        "|------|---------|-----------|----------------|",
    ]

    for entry in ranked[:20]:
        freq_pct = f"{entry['frequency'] * 100:.0f}%"  # type: ignore[operator]
        lines.append(
            f"| `{entry['test_id']}` | {entry['failures']}/{runs} | {freq_pct} | {entry['label']} |"
        )

    lines += ["", "## Suggested Actions", ""]
    for entry in ranked[:5]:
        first_bad = find_first_bad_commit(str(entry["test_id"]))
        lines.append(f"### `{entry['test_id']}`")
        lines.append(f"- Classification: **{entry['label']}**")
        lines.append(f"- Failures: {entry['failures']}/{runs} runs")
        if first_bad:
            lines.append(f"- Last commit touching this file: `{first_bad}`")
        if "CONSISTENTLY" in str(entry["label"]):
            lines.append("- Action: Fix immediately — this is not flaky, it's broken.")
        else:
            lines.append("- Action: Add `@pytest.mark.flaky(reruns=3)` or investigate ordering deps.")
        lines.append("")

    report_text = "\n".join(lines)

    if report_path:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")
        ok("Report", f"Report written to {report_path}")
    else:
        print()
        for line in lines[:30]:
            print(f"  {line}")
        if len(lines) > 30:
            print(f"  ... ({len(lines) - 30} more lines)")


def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  FLAKY TEST HUNTER SUMMARY")
    print("=" * 60)

    if not findings:
        print("  No flaky tests detected. Test suite is stable.")
        print("=" * 60)
        return

    by_severity: dict[str, list[dict[str, str]]] = {}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        print(f"\n  [{sev}] — {len(items)} finding(s):")
        for item in items:
            print(f"    [{item['category']}] {item['message'][:100]}")

    print(f"\n  Total: {len(findings)} issue(s) across {len(by_severity)} severity level(s).")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="DocReview360 flaky-test hunter.")
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Number of times to run the test suite (default: 2)",
    )
    parser.add_argument("--test-path", default=None, help="Specific test path to run")
    parser.add_argument(
        "--report",
        default=None,
        help="Output path for flaky-test markdown report",
    )
    args = parser.parse_args()

    print("DocReview360 Flaky Test Hunter")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Runs: {args.runs}")
    if args.test_path:
        print(f"Test path: {args.test_path}")

    per_test_failures = hunt_flaky(args.runs, args.test_path)
    ranked = rank_by_frequency(per_test_failures, args.runs)
    report_path = Path(args.report) if args.report else None
    write_report(ranked, args.runs, report_path)
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
