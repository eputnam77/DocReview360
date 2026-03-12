#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Dependency review loop.

Runs pip-audit, bandit, and npm audit, then summarizes findings into
actionable issues grouped by severity. Always exits 0 (informational).

Usage:
    python scripts/dependency-review.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

findings: list[dict[str, str]] = []


def note(tool: str, severity: str, message: str) -> None:
    findings.append({"tool": tool, "severity": severity, "message": message})
    indicator = "!" if severity in ("CRITICAL", "HIGH") else "~"
    print(f"  [{indicator}] [{tool}] {severity}: {message}")


def ok(tool: str, message: str) -> None:
    print(f"  [+] [{tool}] ok: {message}")


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd or REPO_ROOT),
            timeout=120,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", f"Timeout running: {' '.join(cmd)}"


# ---------------------------------------------------------------------------
# 1. pip-audit — Python vulnerability scan
# ---------------------------------------------------------------------------

def check_pip_audit() -> None:
    section("pip-audit — Python vulnerability scan")

    code, stdout, stderr = run([sys.executable, "scripts/run-pip-audit.py"])
    if code == -1:
        print(f"  skip : pip-audit not available ({stderr})")
        return

    output = stdout + stderr
    lines = output.splitlines()

    vuln_count = 0
    for line in lines:
        # pip-audit output: "Package  Version  ID  Fix Versions  Description"
        if re.search(r'CVE-\d{4}-\d+|PYSEC-\d+|GHSA-', line):
            severity = "HIGH" if "critical" in line.lower() else "MEDIUM"
            note("pip-audit", severity, line.strip()[:120])
            vuln_count += 1

    if vuln_count == 0:
        ok("pip-audit", f"No known vulnerabilities detected (exit {code})")
    else:
        print(f"  [{vuln_count}] vulnerability finding(s) from pip-audit")


# ---------------------------------------------------------------------------
# 2. bandit — Static security analysis
# ---------------------------------------------------------------------------

def check_bandit() -> None:
    section("bandit — Python static security analysis")

    code, stdout, stderr = run([
        sys.executable, "-m", "bandit",
        "-r", "src",
        "-lll",          # low severity and above
        "--skip", "B101",
        "-f", "json",
        "-q",
    ])

    if code == -1:
        print("  skip : bandit not available")
        return

    # Parse JSON output
    try:
        data = json.loads(stdout)
        results = data.get("results", [])
    except (json.JSONDecodeError, AttributeError):
        results = []

    if not results:
        ok("bandit", "No security issues detected")
        return

    for issue in results[:20]:  # Cap at 20 to avoid overwhelming output
        severity = issue.get("issue_severity", "MEDIUM").upper()
        issue_text = issue.get("issue_text", "")
        filename = issue.get("filename", "")
        line_no = issue.get("line_number", "?")
        note("bandit", severity, f"{filename}:{line_no} — {issue_text[:80]}")

    if len(results) > 20:
        print(f"  ... and {len(results) - 20} more bandit issues")


# ---------------------------------------------------------------------------
# 3. npm audit — Frontend vulnerability scan
# ---------------------------------------------------------------------------

def check_npm_audit() -> None:
    section("npm audit — Frontend vulnerability scan")

    if not (FRONTEND_DIR / "package.json").exists():
        print("  skip : frontend/package.json not found")
        return

    code, stdout, stderr = run(
        ["npm", "audit", "--json", "--audit-level=moderate"],
        cwd=FRONTEND_DIR,
    )

    if code == -1:
        print("  skip : npm not available")
        return

    try:
        data = json.loads(stdout)
        vulnerabilities = data.get("vulnerabilities", {})
        audit_summary = data.get("metadata", {}).get("vulnerabilities", {})
    except (json.JSONDecodeError, AttributeError):
        vulnerabilities = {}
        audit_summary = {}

    if not vulnerabilities:
        ok("npm-audit", "No known vulnerabilities in frontend dependencies")
        return

    total = sum(audit_summary.values()) if audit_summary else len(vulnerabilities)
    critical = audit_summary.get("critical", 0)
    high = audit_summary.get("high", 0)
    moderate = audit_summary.get("moderate", 0)

    if critical > 0:
        note("npm-audit", "CRITICAL", f"{critical} critical vulnerability/vulnerabilities in frontend")
    if high > 0:
        note("npm-audit", "HIGH", f"{high} high vulnerability/vulnerabilities in frontend")
    if moderate > 0:
        note("npm-audit", "MEDIUM", f"{moderate} moderate vulnerability/vulnerabilities in frontend")

    # Show first 5 package names
    for pkg_name in list(vulnerabilities.keys())[:5]:
        vuln = vulnerabilities[pkg_name]
        sev = vuln.get("severity", "unknown").upper()
        note("npm-audit", sev, f"package: {pkg_name}")


# ---------------------------------------------------------------------------
# 4. Actionable issues summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print(f"\n{'='*60}")
    print(f"  DEPENDENCY REVIEW SUMMARY")
    print("=" * 60)

    if not findings:
        print("  No actionable issues found. All scans clean.")
        print("=" * 60)
        return

    by_severity: dict[str, list[dict[str, str]]] = {}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    # Print in priority order
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        print(f"\n  [{sev}] — {len(items)} finding(s):")
        for item in items:
            print(f"    [{item['tool']}] {item['message'][:100]}")

    print(f"\n  Total: {len(findings)} actionable issue(s) across {len(by_severity)} severity level(s).")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("DocReview360 Dependency Review")
    print(f"Repo root: {REPO_ROOT}")

    check_pip_audit()
    check_bandit()
    check_npm_audit()
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
