#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Accessibility check loop for the Next.js frontend.

Runs eslint (with jsx-a11y plugin) and source-level checks for common
accessibility regressions. Captures findings for human review.
Always exits 0 (informational).

Does not require a running browser — works in CI/headless environments.
For full axe/Playwright checks, see docs/e2e.md.

Usage:
    python scripts/accessibility-check.py
    python scripts/accessibility-check.py --output artifacts/a11y-report.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

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


# ---------------------------------------------------------------------------
# 1. ESLint jsx-a11y (if available)
# ---------------------------------------------------------------------------

def check_eslint_a11y() -> None:
    section("ESLint jsx-a11y Accessibility Lint")

    if not FRONTEND_DIR.exists():
        skip("ESLint", "frontend/ directory not found")
        return

    eslint_config = FRONTEND_DIR / ".eslintrc.js"
    if not eslint_config.exists():
        eslint_config = FRONTEND_DIR / ".eslintrc.json"
    if not eslint_config.exists():
        eslint_config = FRONTEND_DIR / ".eslintrc"

    if eslint_config.exists():
        cfg_text = eslint_config.read_text(encoding="utf-8")
        if "jsx-a11y" in cfg_text:
            ok("ESLint", "jsx-a11y plugin configured in ESLint config")
        else:
            note("ESLint", "LOW", "jsx-a11y plugin not in ESLint config — add eslint-plugin-jsx-a11y")
    else:
        # Check package.json for the plugin
        pkg = FRONTEND_DIR / "package.json"
        if pkg.exists():
            pkg_text = pkg.read_text(encoding="utf-8")
            if "jsx-a11y" in pkg_text:
                ok("ESLint", "eslint-plugin-jsx-a11y listed in package.json")
            else:
                note("ESLint", "LOW", "eslint-plugin-jsx-a11y not in package.json — no automated a11y linting")

    # Try running eslint
    try:
        result = subprocess.run(
            ["npm", "run", "lint", "--", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(FRONTEND_DIR),
            timeout=60,
        )
        if result.returncode == 0:
            ok("ESLint", "npm run lint passed (no ESLint errors)")
        else:
            # Try to parse output
            output = result.stdout or result.stderr
            a11y_issues = [line for line in output.splitlines() if "a11y" in line.lower() or "accessible" in line.lower()]
            if a11y_issues:
                for issue in a11y_issues[:5]:
                    note("ESLint", "MEDIUM", f"a11y lint: {issue[:100]}")
            else:
                note("ESLint", "LOW", f"npm run lint failed (exit {result.returncode}) — check output")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        skip("ESLint", "npm not available or timed out")


# ---------------------------------------------------------------------------
# 2. Source-level checks
# ---------------------------------------------------------------------------

def _scan_tsx_files() -> list[Path]:
    pages = list((FRONTEND_DIR / "pages").rglob("*.tsx")) if (FRONTEND_DIR / "pages").exists() else []
    components = list((FRONTEND_DIR / "components").rglob("*.tsx")) if (FRONTEND_DIR / "components").exists() else []
    return pages + components


def check_image_alt_attributes() -> None:
    section("Image Alt Attributes")

    files = _scan_tsx_files()
    if not files:
        skip("Images", "No .tsx files found in pages/ or components/")
        return

    ok("Images", f"Scanning {len(files)} TSX file(s) for img alt attributes")

    issues = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        # Find <img> or <Image> without alt
        for m in re.finditer(r"<(?:img|Image)\s[^>]*>", text, re.DOTALL):
            tag = m.group(0)
            if "alt=" not in tag:
                rel = path.relative_to(REPO_ROOT)
                line_num = text[:m.start()].count("\n") + 1
                issues.append(f"{rel}:{line_num} — <img> missing alt attribute")

    if issues:
        for issue in issues[:10]:
            note("Images", "HIGH", issue)
        if len(issues) > 10:
            note("Images", "MEDIUM", f"... and {len(issues) - 10} more missing alt attributes")
    else:
        ok("Images", "All <img>/<Image> tags have alt attributes (or none found)")


def check_button_accessibility() -> None:
    section("Button Accessibility")

    files = _scan_tsx_files()
    issues = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        # Button with only icon (no aria-label or visible text)
        for m in re.finditer(r'<button[^>]*>\s*(?:<[^>]+/>|<[^>]+></[^>]+>)\s*</button>', text, re.DOTALL):
            btn = m.group(0)
            if "aria-label" not in btn and "title=" not in btn:
                rel = path.relative_to(REPO_ROOT)
                line_num = text[:m.start()].count("\n") + 1
                issues.append(f"{rel}:{line_num} — icon-only button missing aria-label")

    if issues:
        for issue in issues[:5]:
            note("Buttons", "MEDIUM", issue)
    else:
        ok("Buttons", "No icon-only buttons without aria-label found")


def check_form_labels() -> None:
    section("Form Label Associations")

    files = _scan_tsx_files()
    issues = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        # Find <input> without id or aria-label
        for m in re.finditer(r'<input\s[^>]*(?:type="text"|type="email"|type="password"|type="search")[^>]*/?\s*>', text):
            inp = m.group(0)
            if "id=" not in inp and "aria-label=" not in inp and "aria-labelledby=" not in inp:
                rel = path.relative_to(REPO_ROOT)
                line_num = text[:m.start()].count("\n") + 1
                issues.append(f"{rel}:{line_num} — <input> missing id/aria-label for label association")

    if issues:
        for issue in issues[:5]:
            note("Forms", "MEDIUM", issue)
    else:
        ok("Forms", "No unlabelled form inputs detected")


def check_heading_hierarchy() -> None:
    section("Heading Hierarchy")

    files = _scan_tsx_files()
    multi_h1 = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        h1_count = len(re.findall(r'<h1[\s>]', text))
        if h1_count > 1:
            rel = path.relative_to(REPO_ROOT)
            multi_h1.append(f"{rel}: {h1_count} <h1> elements (should be 1 per page)")

    if multi_h1:
        for issue in multi_h1:
            note("Headings", "MEDIUM", issue)
    else:
        ok("Headings", "No pages with multiple <h1> elements detected")


def check_color_contrast_patterns() -> None:
    section("Color Contrast Patterns (Source-level Heuristics)")

    files = _scan_tsx_files()

    # Check for hardcoded light-on-light or dark-on-dark text patterns
    suspicious = []
    bad_patterns = [
        (r'text-gray-[1-3]00\s+bg-gray-[1-3]00', "light-gray on light-gray"),
        (r'text-white.*bg-yellow-[1-3]00', "white on light-yellow"),
        (r'text-gray-200\s', "very light gray text (potential low contrast)"),
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern, label in bad_patterns:
            if re.search(pattern, text):
                rel = path.relative_to(REPO_ROOT)
                suspicious.append(f"{rel}: potential {label}")

    if suspicious:
        for issue in suspicious[:5]:
            note("Contrast", "LOW", issue)
    else:
        ok("Contrast", "No obvious low-contrast patterns detected in source")


def check_aria_roles() -> None:
    section("ARIA Roles and Labels")

    files = _scan_tsx_files()
    ok("ARIA", f"Scanning {len(files)} TSX file(s) for ARIA usage")

    aria_usage = 0
    role_usage = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        if "aria-" in text:
            aria_usage += 1
        if 'role="' in text:
            role_usage += 1

    ok("ARIA", f"aria-* attributes used in {aria_usage} file(s)")
    ok("ARIA", f'role="..." used in {role_usage} file(s)')

    if aria_usage == 0 and len(files) > 5:
        note("ARIA", "MEDIUM", "No aria-* attributes found in any component — accessibility may be poor")


def check_keyboard_navigation() -> None:
    section("Keyboard Navigation (Source Heuristics)")

    files = _scan_tsx_files()
    tab_index_files = []
    negative_tab = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        if "tabIndex" in text or "tabindex" in text:
            tab_index_files.append(path.relative_to(REPO_ROOT))
            if "tabIndex={-1}" in text or 'tabindex="-1"' in text:
                negative_tab.append(str(path.relative_to(REPO_ROOT)))

    if tab_index_files:
        ok("Keyboard", f"tabIndex used in {len(tab_index_files)} file(s)")
    if negative_tab:
        note("Keyboard", "LOW", f"tabIndex=-1 (skipped elements): {', '.join(negative_tab[:3])}")
    else:
        ok("Keyboard", "No tabIndex=-1 (removed from tab order) detected")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_report(output_path: Path | None) -> None:
    if not output_path or not findings:
        return

    lines = [
        "# Accessibility Check Report (DRAFT)",
        "",
        "> Auto-generated by `scripts/accessibility-check.py`.",
        "> Review manually and fix HIGH/MEDIUM findings before release.",
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
    ok("Report", f"Accessibility report written to {output_path}")


def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  ACCESSIBILITY CHECK SUMMARY")
    print("=" * 60)

    if not findings:
        print("  No accessibility issues detected. All checks passed.")
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
    parser = argparse.ArgumentParser(description="DocReview360 accessibility check loop.")
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for accessibility report markdown",
    )
    args = parser.parse_args()

    print("DocReview360 Accessibility Check")
    print(f"Repo root: {REPO_ROOT}")
    print("Note: For full axe/Playwright checks, see docs/e2e.md")

    check_eslint_a11y()
    check_image_alt_attributes()
    check_button_accessibility()
    check_form_labels()
    check_heading_hierarchy()
    check_color_contrast_patterns()
    check_aria_roles()
    check_keyboard_navigation()

    output_path = Path(args.output) if args.output else None
    write_report(output_path)
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
