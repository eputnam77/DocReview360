#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Placeholder and metadata reviewer.

Searches source files for placeholder URLs/emails, TODO/FIXME/PLACEHOLDER
markers, stale license references, and version mismatches.

Exit code is always 0 (informational only).

Usage:
    python scripts/check-placeholders.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Configuration ─────────────────────────────────────────────────────────────

INCLUDE_EXTENSIONS = {".py", ".tsx", ".ts", ".md", ".yaml", ".yml", ".toml", ".sh", ".json"}

SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    "out",
    "coverage",
    "htmlcov",
    ".tox",
    "site-packages",
}

# Patterns: (label, regex)
PLACEHOLDER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("placeholder-url",    re.compile(r'example\.com', re.IGNORECASE)),
    ("placeholder-email",  re.compile(r'info@example\.com', re.IGNORECASE)),
    ("placeholder-registry", re.compile(r'registry\.example\.com', re.IGNORECASE)),
    ("todo",               re.compile(r'\bTODO\b', re.IGNORECASE)),
    ("fixme",              re.compile(r'\bFIXME\b', re.IGNORECASE)),
    ("placeholder-marker", re.compile(r'\bPLACEHOLDER\b', re.IGNORECASE)),
    ("stale-gpl",          re.compile(r'\bGPL\b(?![\w-])')),  # GPL not part of longer word
]

# Files/dirs to skip for GPL check specifically (license history, etc.)
GPL_SKIP_PATHS = {
    "RELEASE_CHECKLIST.md",   # mentions "stale GPL references" legitimately
    "MEMORY.md",
    "CLAUDE.md",
    "CLAUDE_CODE_UPDATES.md",
    "ai-notes.md",
    "docs/licenses-report.md",
    "scripts/check-placeholders.py",  # this file itself
}

# ── Helpers ───────────────────────────────────────────────────────────────────

Finding = tuple[str, int, str, str]  # (file_rel, lineno, label, matched_text)


def should_skip_dir(part: str) -> bool:
    if part in SKIP_DIRS:
        return True
    if part.startswith("."):
        return True
    # Skip stray Python prefix directories at any level (e.g., "3.12", "3.11")
    if re.match(r'^\d+\.\d+$', part):
        return True
    return False


def iter_files() -> list[Path]:
    results: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        # Skip hidden/excluded dirs
        rel_parts = path.relative_to(REPO_ROOT).parts
        if any(should_skip_dir(p) for p in rel_parts[:-1]):
            continue
        if path.suffix.lower() not in INCLUDE_EXTENSIONS:
            continue
        results.append(path)
    return sorted(results)


def get_pkg_version() -> str:
    pyproject = REPO_ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return m.group(1) if m else ""


def scan_file(path: Path, pkg_version: str) -> list[Finding]:
    rel = str(path.relative_to(REPO_ROOT))
    findings: list[Finding] = []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return findings

    lines = text.splitlines()

    # Skip this script for all pattern checks
    if rel == "scripts/check-placeholders.py":
        return findings

    for lineno, line in enumerate(lines, 1):
        for label, pattern in PLACEHOLDER_PATTERNS:
            # Skip GPL check for known-legitimate files
            if label == "stale-gpl" and rel in GPL_SKIP_PATHS:
                continue
            # Skip GPL check for SPDX comment lines (these are correct)
            if label == "stale-gpl" and "SPDX-License-Identifier" in line:
                continue
            # Skip example.com in the check-placeholders script itself
            if pattern.search(line):
                m = pattern.search(line)
                findings.append((rel, lineno, label, m.group(0) if m else ""))

    return findings


# ── Version consistency ───────────────────────────────────────────────────────

def check_version_consistency(pkg_version: str) -> list[Finding]:
    """Find version strings in key files that don't match pyproject.toml."""
    if not pkg_version:
        return []

    findings: list[Finding] = []
    # Files that typically embed the version
    key_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "src" / "docreview360" / "__init__.py",
        REPO_ROOT / "helm" / "docreview360" / "Chart.yaml",
        REPO_ROOT / "helm" / "docreview360" / "values.yaml",
    ]
    # Pattern: a version-like string near "version" that differs from pkg_version
    version_pattern = re.compile(r'(?:version|Version)\s*[=:]\s*["\']?(\d+\.\d+\.\d+)["\']?')

    for fpath in key_files:
        if not fpath.exists():
            continue
        text = fpath.read_text(encoding="utf-8", errors="replace")
        rel = str(fpath.relative_to(REPO_ROOT))
        for lineno, line in enumerate(text.splitlines(), 1):
            m = version_pattern.search(line)
            if m:
                found_ver = m.group(1)
                if found_ver != pkg_version:
                    findings.append((
                        rel, lineno, "version-mismatch",
                        f"found {found_ver!r}, expected {pkg_version!r}"
                    ))
    return findings


# ── Report ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("DocReview360 Placeholder and Metadata Reviewer")
    print(f"Repo root: {REPO_ROOT}")
    print()

    pkg_version = get_pkg_version()
    if pkg_version:
        print(f"Package version from pyproject.toml: {pkg_version}")
    else:
        print("WARNING: Could not parse version from pyproject.toml")
    print()

    all_findings: list[Finding] = []

    files = iter_files()
    print(f"Scanning {len(files)} files...")

    for path in files:
        file_findings = scan_file(path, pkg_version)
        all_findings.extend(file_findings)

    # Version consistency check
    version_findings = check_version_consistency(pkg_version)
    all_findings.extend(version_findings)

    # Group by label for summary
    by_label: dict[str, list[Finding]] = {}
    for f in all_findings:
        by_label.setdefault(f[2], []).append(f)

    if not all_findings:
        print("No placeholder or metadata issues found.")
        sys.exit(0)

    # Print findings grouped by type
    label_order = [
        "placeholder-url",
        "placeholder-email",
        "placeholder-registry",
        "stale-gpl",
        "version-mismatch",
        "placeholder-marker",
        "todo",
        "fixme",
    ]

    for label in label_order:
        items = by_label.get(label, [])
        if not items:
            continue
        print(f"\n{'─'*60}")
        print(f"  [{label.upper()}] — {len(items)} occurrence(s)")
        print("─"*60)
        for rel, lineno, lbl, matched in items[:50]:  # cap at 50 per category
            print(f"  {rel}:{lineno}  →  {matched!r}")
        if len(items) > 50:
            print(f"  ... and {len(items) - 50} more")

    # Remaining labels not in the ordered list
    for label, items in sorted(by_label.items()):
        if label in label_order:
            continue
        print(f"\n{'─'*60}")
        print(f"  [{label.upper()}] — {len(items)} occurrence(s)")
        print("─"*60)
        for rel, lineno, lbl, matched in items[:50]:
            print(f"  {rel}:{lineno}  →  {matched!r}")

    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(all_findings)} total finding(s) across {len(by_label)} categories.")
    for label, items in sorted(by_label.items()):
        print(f"  {label}: {len(items)}")
    print("="*60)

    # Always exit 0 (informational)
    sys.exit(0)


if __name__ == "__main__":
    main()
