#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Docs broken-link and drift checker for DocReview360.

Scans all Markdown files under docs/ and the root README.md for:
  - Relative file links that point to non-existent files
  - Placeholder URLs (example.com, registry.example.com)
  - Stale GPL license references (project is now MIT)
  - Placeholder contact emails (example.com)
  - References to removed modules or files

Always exits 0 (informational). Prints a SUMMARY section at the end.

Usage:
    python scripts/check-docs-links.py
    python scripts/check-docs-links.py --output artifacts/docs-links-report.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

findings: list[dict[str, str]] = []


def note(category: str, severity: str, message: str) -> None:
    findings.append({"category": category, "severity": severity, "message": message})
    indicator = "!" if severity in ("CRITICAL", "HIGH") else "~"
    print(f"  [{indicator}] [{category}] {severity}: {message}")


def ok(category: str, message: str) -> None:
    print(f"  [+] [{category}] ok: {message}")


def skip(category: str, message: str) -> None:
    print(f"  [~] [{category}] skip: {message}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def _markdown_files() -> list[Path]:
    files: list[Path] = []
    if DOCS_DIR.exists():
        files.extend(DOCS_DIR.rglob("*.md"))
    readme = REPO_ROOT / "README.md"
    if readme.exists():
        files.append(readme)
    changelog = REPO_ROOT / "CHANGELOG.md"
    if changelog.exists():
        files.append(changelog)
    security = REPO_ROOT / "SECURITY.md"
    if security.exists():
        files.append(security)
    return files


# ---------------------------------------------------------------------------
# 1. Relative link validation
# ---------------------------------------------------------------------------

def check_relative_links() -> None:
    section("Relative File Links")

    files = _markdown_files()
    if not files:
        skip("Links", "No Markdown files found")
        return

    ok("Links", f"Scanning {len(files)} Markdown file(s)")
    broken = 0

    # Non-standard URI schemes to skip
    skip_schemes = (
        "http://", "https://", "mailto:", "#", "ftp:", "browser:", "vscode:",
        "jetbrains:", "slack:", "ms-", "jar:",
    )

    for md_file in files:
        text = md_file.read_text(encoding="utf-8")
        # Strip fenced code blocks and inline code spans to avoid false positives
        text_no_code = re.sub(r'```[\s\S]*?```', '', text)
        text_no_code = re.sub(r'`[^`\n]+`', '', text_no_code)
        # Match [text](path) — skip http/https/mailto/anchors
        for m in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', text_no_code):
            link = m.group(2).strip()
            if any(link.startswith(s) for s in skip_schemes):
                continue
            # Skip internal-only dev paths
            if link.startswith(".dev/"):
                continue
            # Strip anchor and title from path (e.g. href "title")
            path_part = link.split("#")[0].split('"')[0].strip()
            if not path_part:
                continue
            target = (md_file.parent / path_part).resolve()
            if not target.exists():
                rel_md = md_file.relative_to(REPO_ROOT)
                line_num = text[: m.start()].count("\n") + 1
                note("Links", "MEDIUM", f"{rel_md}:{line_num} — broken link: {link}")
                broken += 1

    if broken == 0:
        ok("Links", "All relative links resolve to existing files")


# ---------------------------------------------------------------------------
# 2. Placeholder URL scan
# ---------------------------------------------------------------------------

PLACEHOLDER_PATTERNS = [
    (r"example\.com", "example.com URL"),
    (r"registry\.example\.com", "registry.example.com URL"),
    (r"@example\.com", "example.com email address"),
    (r"TODO:|FIXME:", "TODO/FIXME marker"),
]

# These occurrences are acceptable (code examples, tests, ADRs describing old state)
PLACEHOLDER_ALLOWLIST = {
    "RELEASE_CHECKLIST.md",
    "docs/websocket_proxy_guide.md",  # example.com in nginx config examples
    "docs/audit_log_schema.md",       # example.com in example cert URL
    "docs/api_overview.md",           # example.com in webhook example
}


def check_placeholders() -> None:
    section("Placeholder URLs and Emails")

    files = _markdown_files()
    found = 0

    for md_file in files:
        rel = md_file.relative_to(REPO_ROOT)
        rel_str = str(rel)
        if any(allowed in rel_str for allowed in PLACEHOLDER_ALLOWLIST):
            skip("Placeholders", f"Skipping allowlisted file: {rel}")
            continue
        text = md_file.read_text(encoding="utf-8")
        for pattern, label in PLACEHOLDER_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                line_num = text[: m.start()].count("\n") + 1
                note("Placeholders", "LOW", f"{rel}:{line_num} — {label}: {m.group(0)[:60]}")
                found += 1

    if found == 0:
        ok("Placeholders", "No placeholder URLs or emails found")


# ---------------------------------------------------------------------------
# 3. Stale GPL references
# ---------------------------------------------------------------------------

GPL_ALLOWLIST = {
    "docs/licenses.md",          # mentions LGPL dependencies — expected
    "docs/licenses-report.md",   # mentions LGPL/GPL transitive deps — expected
    "RELEASE_CHECKLIST.md",
}


def check_gpl_references() -> None:
    section("Stale GPL License References")

    files = _markdown_files()
    found = 0

    for md_file in files:
        rel = md_file.relative_to(REPO_ROOT)
        rel_str = str(rel)
        if any(allowed in rel_str for allowed in GPL_ALLOWLIST):
            continue
        text = md_file.read_text(encoding="utf-8")
        # Look for "GPL-3.0-only" or "licensed under GPL" type references
        for m in re.finditer(r'GPL-3\.0-only|licensed under GPL|under GPL-3', text, re.IGNORECASE):
            line_num = text[: m.start()].count("\n") + 1
            note(
                "License",
                "MEDIUM",
                f"{rel}:{line_num} — stale GPL reference: {m.group(0)} (project is now MIT)",
            )
            found += 1

    if found == 0:
        ok("License", "No stale GPL-3.0-only references found outside expected files")


# ---------------------------------------------------------------------------
# 4. Removed module references
# ---------------------------------------------------------------------------

REMOVED_MODULES = [
    ("filelock", "removed from deps (replaced with SQLite persistence)"),
    ("workflow_templates.json", "disk fallback removed (DB-only now)"),
    ("email_templates.json", "disk fallback removed (DB-only now)"),
]


def check_removed_module_refs() -> None:
    section("Removed Module References")

    files = _markdown_files()
    found = 0

    for md_file in files:
        rel = md_file.relative_to(REPO_ROOT)
        text = md_file.read_text(encoding="utf-8")
        for module, reason in REMOVED_MODULES:
            if module in text:
                line_num = next(
                    (i + 1 for i, line in enumerate(text.splitlines()) if module in line),
                    0,
                )
                note(
                    "StaleRefs",
                    "LOW",
                    f"{rel}:{line_num} — references removed module '{module}' ({reason})",
                )
                found += 1

    if found == 0:
        ok("StaleRefs", "No references to removed modules found in docs")


# ---------------------------------------------------------------------------
# Summary and report
# ---------------------------------------------------------------------------

def write_report(output_path: Path | None) -> None:
    if not output_path or not findings:
        return

    lines = [
        "# Docs Link and Drift Report (DRAFT)",
        "",
        "> Auto-generated by `scripts/check-docs-links.py`.",
        "> Review manually and fix MEDIUM/HIGH findings before release.",
        "",
        f"Total findings: {len(findings)}",
        "",
    ]

    by_severity: dict[str, list[dict[str, str]]] = {}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        lines.append(f"## [{sev}] — {len(items)} finding(s)")
        lines.append("")
        for item in items:
            lines.append(f"- **[{item['category']}]** {item['message']}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    ok("Report", f"Docs link report written to {output_path}")


def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  DOCS LINK AND DRIFT CHECK SUMMARY")
    print("=" * 60)

    if not findings:
        print("  No issues detected. All docs link checks passed.")
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
    parser = argparse.ArgumentParser(description="DocReview360 docs link and drift checker.")
    parser.add_argument("--output", default=None, help="Output path for report markdown")
    args = parser.parse_args()

    print("DocReview360 Docs Link and Drift Checker")
    print(f"Repo root: {REPO_ROOT}")

    check_relative_links()
    check_placeholders()
    check_gpl_references()
    check_removed_module_refs()

    output_path = Path(args.output) if args.output else None
    write_report(output_path)
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
