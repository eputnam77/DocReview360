#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Failing-test triage loop.

Watches pytest failures, clusters similar stack traces, drafts the
likely root cause, and proposes the smallest patch.
Always exits 0 (informational).

Usage:
    python scripts/failing-test-triage.py
    python scripts/failing-test-triage.py --test-path tests/test_approvals.py
    python scripts/failing-test-triage.py --json-report artifacts/triage.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "triage"

findings: list[dict[str, str]] = []
clusters: list[dict[str, object]] = []


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


# ---------------------------------------------------------------------------
# 1. Run pytest and capture failures
# ---------------------------------------------------------------------------

def run_pytest(test_path: str | None) -> tuple[int, str]:
    """Run pytest in fast mode and return (returncode, combined output)."""
    section("Running pytest")

    cmd = [
        sys.executable, "-m", "pytest",
        "--tb=short", "-q",
        "--ignore=_debug_test.py",
        "--ignore=tests/test_auth_repository.py",
        "--no-header",
    ]
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")

    env_patch = {"DOCREVIEW360_ENV": "dev"}
    import os  # noqa: PLC0415
    env = {**os.environ, **env_patch}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=300,
            env=env,
        )
        combined = result.stdout + result.stderr
        ok("pytest", f"Run completed: exit {result.returncode}")
        return result.returncode, combined
    except subprocess.TimeoutExpired:
        note("pytest", "HIGH", "pytest timed out after 300s")
        return -1, ""


# ---------------------------------------------------------------------------
# 2. Parse failures from pytest output
# ---------------------------------------------------------------------------

FAILURE_RE = re.compile(r"FAILED\s+([\w/.:\[\]-]+)\s*-?\s*(.*)")
TRACEBACK_SEP = re.compile(r"_{5,}\s+([\w/:.\[\]-]+)\s*_{5,}")
ERROR_TYPE_RE = re.compile(r"([\w.]+Error|[\w.]+Exception|AssertionError|ImportError)[:\s]")


def parse_failures(output: str) -> list[dict[str, str]]:
    """Extract failure entries from pytest short-traceback output."""
    section("Parsing Failures")

    failures = []
    for m in FAILURE_RE.finditer(output):
        test_id = m.group(1).strip()
        short_reason = m.group(2).strip()[:120]
        failures.append({"test_id": test_id, "reason": short_reason})

    ok("Parser", f"Found {len(failures)} failing test(s)")
    return failures


# ---------------------------------------------------------------------------
# 3. Cluster by error type
# ---------------------------------------------------------------------------

def cluster_failures(output: str, failures: list[dict[str, str]]) -> list[dict[str, object]]:
    """Cluster failures by dominant error type."""
    section("Clustering by Error Type")

    error_buckets: dict[str, list[str]] = defaultdict(list)

    for failure in failures:
        reason = failure["reason"]
        m = ERROR_TYPE_RE.search(reason)
        error_type = m.group(1) if m else "Unknown"
        error_buckets[error_type].append(failure["test_id"])

    # Also scan the full output for error types
    for m in ERROR_TYPE_RE.finditer(output):
        pass  # just for summary

    result_clusters = []
    for error_type, test_ids in sorted(error_buckets.items(), key=lambda x: -len(x[1])):
        cluster = {
            "error_type": error_type,
            "count": len(test_ids),
            "tests": test_ids[:10],
            "root_cause": _infer_root_cause(error_type, output),
            "suggested_action": _suggest_action(error_type, output),
        }
        result_clusters.append(cluster)
        severity = "HIGH" if len(test_ids) >= 5 else "MEDIUM"
        note(
            "Cluster",
            severity,
            f"{error_type}: {len(test_ids)} test(s) — {cluster['root_cause'][:80]}",
        )

    return result_clusters


def _infer_root_cause(error_type: str, output: str) -> str:
    """Heuristic root cause inference."""
    lower = output.lower()

    if "importerror" in error_type.lower() or "modulenotfounderror" in error_type.lower():
        m = re.search(r"No module named '([^']+)'", output)
        if m:
            return f"Missing dependency: {m.group(1)}"
        return "Missing Python dependency or broken import"

    if "assertionerror" in error_type.lower():
        if "401" in output or "403" in output:
            return "Auth guard active — test may need credentials"
        if "404" in output:
            return "Endpoint not found — route may have been renamed or removed"
        if "422" in output:
            return "Request validation failure — check request body/schema"
        return "Test assertion failed — value mismatch or unexpected state"

    if "attributeerror" in error_type.lower():
        m = re.search(r"'(\w+)' object has no attribute '(\w+)'", output)
        if m:
            return f"AttributeError: {m.group(1)}.{m.group(2)} does not exist"
        return "Attribute access on None or wrong type"

    if "typeerror" in error_type.lower():
        return "Type mismatch — possibly None passed where value expected"

    if "valueerror" in error_type.lower():
        return "Invalid value — check data shape or parsing logic"

    if "connectionerror" in error_type.lower() or "refused" in lower:
        return "Connection refused — service may not be running"

    return f"{error_type} — inspect stack trace for details"


def _suggest_action(error_type: str, output: str) -> str:
    """Suggest a minimal action for the given error type."""
    lower = output.lower()

    if "importerror" in error_type.lower():
        m = re.search(r"No module named '([^']+)'", output)
        if m:
            pkg = m.group(1).split(".")[0]
            return f"Run: uv pip install {pkg}"
        return "Check pyproject.toml [dev] extras and reinstall"

    if "assertionerror" in error_type.lower():
        if "401" in output:
            return "Add auth headers or use DOCREVIEW360_ENV=dev"
        if "404" in output:
            return "Check endpoint path matches router prefix"
        if "422" in output:
            return "Print response body and fix request schema"
        return "Add a print/breakpoint to inspect actual vs expected values"

    if "attributeerror" in error_type.lower():
        return "Add None-check or verify the object type before attribute access"

    if "typeerror" in error_type.lower():
        return "Add type annotations and run mypy --strict on the affected module"

    return "Run the failing test in isolation with -s flag to see full output"


# ---------------------------------------------------------------------------
# 4. Write report
# ---------------------------------------------------------------------------

def write_report(
    failures: list[dict[str, str]],
    result_clusters: list[dict[str, object]],
    output_json: Path | None,
) -> None:
    section("Triage Report")

    if not failures:
        ok("Report", "No failures to report — all tests pass")
        return

    print(f"\n  {len(failures)} failing test(s) across {len(result_clusters)} cluster(s):\n")

    for cluster in result_clusters:
        print(f"  [{cluster['error_type']}] — {cluster['count']} test(s)")
        print(f"    Root cause:  {cluster['root_cause']}")
        print(f"    Action:      {cluster['suggested_action']}")
        if cluster["tests"]:
            for t in cluster["tests"][:3]:  # type: ignore[union-attr]
                print(f"      - {t}")
            if len(cluster["tests"]) > 3:  # type: ignore[arg-type]
                print(f"      ... and {len(cluster['tests']) - 3} more")  # type: ignore[arg-type]
        print()

    if output_json:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        report = {
            "failures": failures,
            "clusters": result_clusters,
            "total_failures": len(failures),
        }
        output_json.write_text(json.dumps(report, indent=2))
        ok("Report", f"JSON report written to {output_json}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  FAILING-TEST TRIAGE SUMMARY")
    print("=" * 60)

    if not findings:
        print("  All tests pass — no failures to triage.")
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
    parser = argparse.ArgumentParser(description="DocReview360 failing-test triage loop.")
    parser.add_argument("--test-path", default=None, help="Specific test path to run")
    parser.add_argument(
        "--json-report",
        default=None,
        help="Output path for JSON triage report",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip running pytest (useful when piping existing output)",
    )
    args = parser.parse_args()

    print("DocReview360 Failing-Test Triage Loop")
    print(f"Repo root: {REPO_ROOT}")

    output_json = Path(args.json_report) if args.json_report else None

    if args.skip_run:
        note("pytest", "LOW", "Skipping pytest run (--skip-run)")
        output = ""
    else:
        _rc, output = run_pytest(args.test_path)

    failures = parse_failures(output)
    result_clusters = cluster_failures(output, failures) if failures else []
    write_report(failures, result_clusters, output_json)
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
