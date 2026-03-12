#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Packaging auditor.

Inspects pyproject.toml package-data rules, MANIFEST.in (if present),
.dockerignore, and the dist/ directory for potential junk that should not
be shipped to PyPI or Docker.

This is an informational script — exit code is always 0.

Usage:
    python scripts/packaging-audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
MANIFEST_IN = REPO_ROOT / "MANIFEST.in"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
DIST_DIR = REPO_ROOT / "dist"

# Files/patterns that should NOT appear in the wheel or sdist.
JUNK_PATTERNS = [
    re.compile(r"tests/"),
    re.compile(r"_debug_test\.py"),
    re.compile(r"ai-notes\.md"),
    re.compile(r"push-after-fix\.ps1"),
    re.compile(r"artifacts/"),
    re.compile(r"node_modules/"),
    re.compile(r"\.next/"),
    re.compile(r"frontend/pages__backup"),
    re.compile(r"\.log$"),
    re.compile(r"\.db$"),
    re.compile(r"\.lock$"),
    re.compile(r"htmlcov/"),
    re.compile(r"\.coverage"),
]

findings: list[str] = []


def note(msg: str) -> None:
    findings.append(msg)
    print(f"  WARN : {msg}")


def ok(msg: str) -> None:
    print(f"  ok   : {msg}")


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 1. pyproject.toml package-data rules
# ---------------------------------------------------------------------------

def check_package_data() -> None:
    section("pyproject.toml package-data rules")
    text = PYPROJECT.read_text(encoding="utf-8")

    # Check for the broad wildcard rule
    if re.search(r'"\*"\s*=\s*\[', text):
        note(
            "Broad wildcard rule '*' = [...] in package-data may include unintended files."
            " Consider replacing with explicit patterns."
        )
    else:
        ok("No broad wildcard '*' = [...] rule found in package-data.")

    # Check tests/ exclusion in packages.find
    if "exclude" in text and "tests" in text:
        ok("tests/ excluded from packages.find.")
    else:
        note("tests/ not excluded in [tool.setuptools.packages.find].")

    # Check .py type marker
    if "py.typed" in text:
        ok("py.typed marker included in package-data.")
    else:
        note("py.typed marker not found in package-data.")


# ---------------------------------------------------------------------------
# 2. MANIFEST.in
# ---------------------------------------------------------------------------

def check_manifest() -> None:
    section("MANIFEST.in")
    if not MANIFEST_IN.exists():
        ok("No MANIFEST.in found — setuptools uses auto-discovery only.")
        return

    text = MANIFEST_IN.read_text(encoding="utf-8")
    if "prune tests" in text or "exclude tests" in text:
        ok("MANIFEST.in explicitly prunes/excludes tests/.")
    else:
        note("MANIFEST.in does not prune tests/ — check if tests are excluded from sdist.")

    if "node_modules" in text or "exclude node_modules" in text:
        ok("MANIFEST.in references node_modules exclusion.")
    else:
        note("MANIFEST.in does not mention node_modules — may be included if glob is broad.")


# ---------------------------------------------------------------------------
# 3. .dockerignore
# ---------------------------------------------------------------------------

def check_dockerignore() -> None:
    section(".dockerignore")
    if not DOCKERIGNORE.exists():
        note(".dockerignore not found — Docker build context may include everything.")
        return

    text = DOCKERIGNORE.read_text(encoding="utf-8")
    checks = [
        ("node_modules/", "node_modules"),
        ("tests/", "tests"),
        (".next/", ".next"),
        (".venv/", ".venv"),
        ("__pycache__/", "__pycache__"),
    ]
    for label, pattern in checks:
        if pattern in text:
            ok(f".dockerignore excludes {label}")
        else:
            note(f".dockerignore does not explicitly exclude {label}")


# ---------------------------------------------------------------------------
# 4. dist/ directory inspection (if present)
# ---------------------------------------------------------------------------

def check_dist() -> None:
    section("dist/ directory")
    if not DIST_DIR.exists():
        ok("No dist/ directory found — nothing built yet.")
        return

    wheels = list(DIST_DIR.glob("*.whl"))
    tarballs = list(DIST_DIR.glob("*.tar.gz"))

    if not wheels and not tarballs:
        ok("dist/ exists but contains no wheels or tarballs.")
        return

    print(f"  Found {len(wheels)} wheel(s) and {len(tarballs)} tarball(s) in dist/")

    # We can't inspect the wheel contents without unzipping, but we can check filenames
    for whl in wheels:
        size_kb = whl.stat().st_size // 1024
        print(f"  wheel : {whl.name} ({size_kb} KB)")
        if size_kb > 10_000:
            note(f"Wheel {whl.name} is very large ({size_kb} KB) — may include frontend assets.")
        else:
            ok(f"Wheel {whl.name} size looks reasonable.")

    for tar in tarballs:
        size_kb = tar.stat().st_size // 1024
        print(f"  sdist : {tar.name} ({size_kb} KB)")
        if size_kb > 50_000:
            note(f"Sdist {tar.name} is very large ({size_kb} KB) — may include frontend/node_modules.")
        else:
            ok(f"Sdist {tar.name} size looks reasonable.")


# ---------------------------------------------------------------------------
# 5. Placeholder scan summary
# ---------------------------------------------------------------------------

def check_placeholders() -> None:
    section("Placeholder scan (summary)")
    placeholder_script = REPO_ROOT / "scripts" / "check-placeholders.py"
    if placeholder_script.exists():
        ok("scripts/check-placeholders.py exists — run it for a detailed scan.")
    else:
        note("scripts/check-placeholders.py not found.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("DocReview360 Packaging Auditor")
    print(f"Repo root: {REPO_ROOT}")

    check_package_data()
    check_manifest()
    check_dockerignore()
    check_dist()
    check_placeholders()

    print(f"\n{'='*60}")
    if findings:
        print(f"SUMMARY: {len(findings)} potential packaging issue(s) found (informational).")
        for i, f in enumerate(findings, 1):
            print(f"  {i}. {f}")
    else:
        print("SUMMARY: No packaging issues detected.")
    print("=" * 60)

    # Always exit 0 — informational only
    sys.exit(0)


if __name__ == "__main__":
    main()
