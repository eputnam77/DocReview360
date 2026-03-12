#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Release-note drafter.

Reads merged commits, checklist changes, and user-visible diffs, then
prepares a draft changelog for human review.
Always exits 0 (informational).

Usage:
    python scripts/release-note-drafter.py
    python scripts/release-note-drafter.py --since v0.1.0
    python scripts/release-note-drafter.py --output CHANGELOG_DRAFT.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

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


def run_git(args: list[str]) -> tuple[int, str]:
    """Run a git command and return (returncode, stdout)."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        return result.returncode, result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1, ""


# ---------------------------------------------------------------------------
# 1. Collect commits since a ref
# ---------------------------------------------------------------------------

def collect_commits(since_ref: str | None) -> list[dict[str, str]]:
    section("Collecting Commits")

    if since_ref:
        code, output = run_git(["log", f"{since_ref}..HEAD", "--oneline", "--no-merges"])
    else:
        code, output = run_git(["log", "--oneline", "--no-merges", "-50"])

    if code != 0 or not output:
        note("Commits", "MEDIUM", "No commits found or git unavailable")
        return []

    commits = []
    for line in output.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0], "message": parts[1]})

    ok("Commits", f"Found {len(commits)} commit(s)")
    return commits


# ---------------------------------------------------------------------------
# 2. Categorize commits by conventional commit type
# ---------------------------------------------------------------------------

COMMIT_CATEGORIES = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "refactor": "Refactoring",
    "test": "Tests",
    "chore": "Chores",
    "perf": "Performance",
    "security": "Security",
    "ci": "CI/CD",
    "style": "Style",
}


def categorize_commits(
    commits: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    section("Categorizing Commits")

    categories: dict[str, list[dict[str, str]]] = {}
    uncategorized = []

    for commit in commits:
        msg = commit["message"]
        matched = False
        for prefix, label in COMMIT_CATEGORIES.items():
            if re.match(rf"^{prefix}[\(:!\[]", msg, re.IGNORECASE):
                categories.setdefault(label, []).append(commit)
                matched = True
                break
        if not matched:
            uncategorized.append(commit)

    if uncategorized:
        categories["Other"] = uncategorized

    for cat, items in sorted(categories.items()):
        ok("Categorize", f"{cat}: {len(items)} commit(s)")

    return categories


# ---------------------------------------------------------------------------
# 3. Check CHANGELOG.md for versioning scheme
# ---------------------------------------------------------------------------

def check_changelog() -> None:
    section("CHANGELOG.md")

    changelog = REPO_ROOT / "CHANGELOG.md"
    if not changelog.exists():
        note("Changelog", "MEDIUM", "CHANGELOG.md not found — create one before release")
        return

    text = changelog.read_text(encoding="utf-8")
    ok("Changelog", f"CHANGELOG.md found ({len(text)} chars)")

    # Check for Keep-a-Changelog format
    if "## [Unreleased]" in text or "## Unreleased" in text:
        ok("Changelog", "[Unreleased] section present — correct Keep-a-Changelog format")
    else:
        note("Changelog", "LOW", "No [Unreleased] section — add one for unreleased changes")

    # Check for version headers
    version_headers = re.findall(r"^## \[?v?[\d.]+\]?", text, re.MULTILINE)
    if version_headers:
        ok("Changelog", f"{len(version_headers)} version heading(s) found: {version_headers[:3]}")
    else:
        note("Changelog", "LOW", "No version headers found in CHANGELOG.md")

    if "Added" in text or "Changed" in text or "Fixed" in text:
        ok("Changelog", "Keep-a-Changelog section types (Added/Changed/Fixed) present")


# ---------------------------------------------------------------------------
# 4. Scan checklist for recently completed items
# ---------------------------------------------------------------------------

def collect_checklist_changes() -> list[str]:
    section("Recently Completed Checklist Items")

    checklist = REPO_ROOT / "RELEASE_CHECKLIST.md"
    if not checklist.exists():
        note("Checklist", "LOW", "RELEASE_CHECKLIST.md not found")
        return []

    text = checklist.read_text(encoding="utf-8")
    today = None

    # Look for items marked done with a recent date
    recent_items = []
    for line in text.splitlines():
        if re.search(r"\[x\].*\(20\d\d-\d\d-\d\d\)", line):
            recent_items.append(line.strip())

    ok("Checklist", f"Found {len(recent_items)} completed checklist item(s)")
    return recent_items[-20:]  # Last 20 completed


# ---------------------------------------------------------------------------
# 5. Draft the release notes
# ---------------------------------------------------------------------------

def draft_release_notes(
    categories: dict[str, list[dict[str, str]]],
    checklist_items: list[str],
    since_ref: str | None,
    output_path: Path | None,
) -> None:
    section("Drafting Release Notes")

    lines = [
        "# Release Notes (DRAFT — human review required)",
        "",
        "> This file was auto-generated by `scripts/release-note-drafter.py`.",
        "> Review and edit before publishing.",
        "",
    ]

    if since_ref:
        lines.append(f"## Changes since `{since_ref}`")
    else:
        lines.append("## Recent Changes")
    lines.append("")

    priority_order = [
        "Security", "Features", "Bug Fixes", "Performance",
        "Documentation", "Refactoring", "CI/CD", "Tests", "Chores", "Style", "Other",
    ]
    for cat in priority_order:
        items = categories.get(cat, [])
        if not items:
            continue
        lines.append(f"### {cat}")
        lines.append("")
        for item in items:
            # Strip conventional commit prefix for readability
            msg = re.sub(r"^(feat|fix|docs|refactor|test|chore|perf|security|ci|style)[\(:!]?\s*", "", item["message"], flags=re.IGNORECASE)
            lines.append(f"- {msg}")
        lines.append("")

    if checklist_items:
        lines.append("### Checklist Progress")
        lines.append("")
        for item in checklist_items[:10]:
            # Extract just the item description
            clean = re.sub(r"^-\s*\[x\]\s*", "", item)
            clean = re.sub(r"\s*\(20\d\d-\d\d-\d\d\).*$", "", clean)
            lines.append(f"- {clean[:120]}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**Review checklist before publishing:**")
    lines.append("- [ ] Version number updated in `pyproject.toml`")
    lines.append("- [ ] `[Unreleased]` section in `CHANGELOG.md` moved to versioned heading")
    lines.append("- [ ] All breaking changes called out explicitly")
    lines.append("- [ ] Security fixes credited (without disclosing exploit details)")
    lines.append("")

    draft = "\n".join(lines)

    if output_path:
        output_path.write_text(draft, encoding="utf-8")
        ok("Draft", f"Release notes draft written to {output_path}")
    else:
        print("\n" + "=" * 60)
        print("  DRAFT RELEASE NOTES (preview — first 40 lines)")
        print("=" * 60)
        for line in lines[:40]:
            print(line)
        if len(lines) > 40:
            print(f"  ... ({len(lines) - 40} more lines)")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  RELEASE NOTE DRAFTER SUMMARY")
    print("=" * 60)

    if not findings:
        print("  Draft complete. Review the output before publishing.")
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
    parser = argparse.ArgumentParser(description="DocReview360 release-note drafter.")
    parser.add_argument(
        "--since",
        default=None,
        help="Git ref to compare from (e.g. v0.1.0, HEAD~50)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path for the draft (default: print to stdout)",
    )
    args = parser.parse_args()

    print("DocReview360 Release Note Drafter")
    print(f"Repo root: {REPO_ROOT}")
    if args.since:
        print(f"Collecting changes since: {args.since}")

    commits = collect_commits(args.since)
    categories = categorize_commits(commits) if commits else {}
    checklist_items = collect_checklist_changes()

    output_path = Path(args.output) if args.output else None
    draft_release_notes(categories, checklist_items, args.since, output_path)

    check_changelog()
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
