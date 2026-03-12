#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Issue-grooming loop.

Turns repeated failures or review findings into deduplicated summaries with
severity, repro steps, and file references. Outputs as markdown for human
review — does NOT automatically create GitHub issues.
Always exits 0 (informational).

Usage:
    python scripts/issue-grooming-loop.py
    python scripts/issue-grooming-loop.py --sources all
    python scripts/issue-grooming-loop.py --output artifacts/groomed-issues.md
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
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "grooming"

findings: list[dict[str, str]] = []
issues: list[dict[str, str]] = []


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
# 1. Collect from triage artifacts
# ---------------------------------------------------------------------------

def collect_from_triage() -> list[dict[str, str]]:
    """Load any existing triage JSON artifacts."""
    section("Collecting from Triage Artifacts")

    triage_dir = REPO_ROOT / "artifacts" / "triage"
    collected = []

    if not triage_dir.exists():
        ok("Triage", "No triage artifacts directory — skipping")
        return collected

    for json_file in sorted(triage_dir.glob("*.json"))[-5:]:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            for cluster in data.get("clusters", []):
                for test_id in cluster.get("tests", [])[:3]:
                    collected.append({
                        "source": "triage",
                        "title": f"Failing test: {cluster['error_type']}",
                        "detail": f"{test_id}: {cluster.get('root_cause', '')}",
                        "severity": "HIGH" if cluster.get("count", 0) >= 5 else "MEDIUM",
                        "action": cluster.get("suggested_action", ""),
                        "file_ref": _extract_file(test_id),
                    })
            ok("Triage", f"Loaded {len(data.get('clusters', []))} cluster(s) from {json_file.name}")
        except (json.JSONDecodeError, KeyError):
            pass

    return collected


def _extract_file(test_id: str) -> str:
    """Extract file path from test_id like tests/foo.py::TestClass::test_name."""
    m = re.match(r"([\w/]+\.py)", test_id)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# 2. Collect from bandit scan
# ---------------------------------------------------------------------------

def collect_from_bandit() -> list[dict[str, str]]:
    """Run bandit and collect HIGH/MEDIUM issues."""
    section("Collecting from Bandit Security Scan")

    collected = []
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", "src", "-lll", "--skip", "B101",
             "-f", "json", "-q"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=60,
        )
        data = json.loads(result.stdout or "{}")
        results = data.get("results", [])
        ok("Bandit", f"{len(results)} bandit finding(s)")
        for issue in results[:10]:
            sev = issue.get("issue_severity", "MEDIUM").upper()
            collected.append({
                "source": "bandit",
                "title": f"Security: {issue.get('test_id', 'unknown')} — {issue.get('issue_text', '')[:60]}",
                "detail": f"{issue.get('filename', '')}:{issue.get('line_number', '?')}",
                "severity": sev,
                "action": f"Review {issue.get('filename', '')} line {issue.get('line_number', '?')}",
                "file_ref": issue.get("filename", ""),
            })
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        ok("Bandit", "bandit not available or timed out — skipping")

    return collected


# ---------------------------------------------------------------------------
# 3. Collect from pre-commit hooks
# ---------------------------------------------------------------------------

def collect_from_precommit() -> list[dict[str, str]]:
    """Collect recent pre-commit failures from git log."""
    section("Collecting from Pre-commit Log (recent commits)")

    collected = []
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-merges", "-20"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=10,
        )
        commits = result.stdout.strip().splitlines()
        ok("PreCommit", f"Checked {len(commits)} recent commit(s)")

        # Look for commits that mention fixes/patches to common issues
        for line in commits:
            if re.search(r"\bfix\b.*\btest\b|\bflak\b", line, re.IGNORECASE):
                collected.append({
                    "source": "git",
                    "title": f"Repeated fix pattern: {line[:60]}",
                    "detail": line,
                    "severity": "LOW",
                    "action": "Consider adding a regression test",
                    "file_ref": "",
                })
    except (FileNotFoundError, subprocess.TimeoutExpired):
        ok("PreCommit", "git not available — skipping")

    return collected


# ---------------------------------------------------------------------------
# 4. Deduplicate issues
# ---------------------------------------------------------------------------

def deduplicate(raw_issues: list[dict[str, str]]) -> list[dict[str, str]]:
    """Simple dedup by title prefix (first 50 chars)."""
    section("Deduplicating Issues")

    seen: set[str] = set()
    deduped = []
    for issue in raw_issues:
        key = issue["title"][:50].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(issue)

    ok("Dedup", f"{len(raw_issues)} raw → {len(deduped)} deduplicated issues")
    return deduped


# ---------------------------------------------------------------------------
# 5. Write output
# ---------------------------------------------------------------------------

def write_output(
    deduped: list[dict[str, str]],
    output_path: Path | None,
) -> None:
    section("Groomed Issues Output")

    if not deduped:
        ok("Output", "No issues to groom")
        return

    # Group by severity
    by_severity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for issue in deduped:
        by_severity[issue["severity"]].append(issue)

    lines = [
        "# Groomed Issues (Draft — human review required)",
        "",
        "> Auto-generated by `scripts/issue-grooming-loop.py`.",
        "> Review, edit, and create GitHub issues manually.",
        "",
        f"Total deduplicated issues: {len(deduped)}",
        "",
    ]

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        lines.append(f"## [{sev}] — {len(items)} issue(s)")
        lines.append("")
        for i, issue in enumerate(items, 1):
            lines.append(f"### {i}. {issue['title']}")
            lines.append(f"- **Source**: {issue['source']}")
            lines.append(f"- **Severity**: {issue['severity']}")
            if issue.get("file_ref"):
                lines.append(f"- **File**: `{issue['file_ref']}`")
            if issue.get("detail"):
                lines.append(f"- **Detail**: {issue['detail'][:120]}")
            if issue.get("action"):
                lines.append(f"- **Suggested action**: {issue['action']}")
            lines.append("")

    report = "\n".join(lines)

    if output_path:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        ok("Output", f"Groomed issues written to {output_path}")
    else:
        for line in lines[:40]:
            print(f"  {line}")
        if len(lines) > 40:
            print(f"  ... ({len(lines) - 40} more lines)")

    # Print severity summary
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        items = by_severity.get(sev, [])
        if items:
            note("Issues", sev, f"{len(items)} {sev} issue(s) need review")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  ISSUE GROOMING SUMMARY")
    print("=" * 60)

    if not findings:
        print("  No issues found to groom. Repository is clean.")
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
    parser = argparse.ArgumentParser(description="DocReview360 issue-grooming loop.")
    parser.add_argument(
        "--sources",
        default="all",
        choices=["all", "triage", "bandit", "git"],
        help="Which sources to collect from (default: all)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for groomed issues markdown",
    )
    args = parser.parse_args()

    print("DocReview360 Issue Grooming Loop")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Sources: {args.sources}")

    all_raw: list[dict[str, str]] = []

    if args.sources in ("all", "triage"):
        all_raw.extend(collect_from_triage())

    if args.sources in ("all", "bandit"):
        all_raw.extend(collect_from_bandit())

    if args.sources in ("all", "git"):
        all_raw.extend(collect_from_precommit())

    deduped = deduplicate(all_raw)
    output_path = Path(args.output) if args.output else None
    write_output(deduped, output_path)
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
