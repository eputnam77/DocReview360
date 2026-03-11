#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Docs drift checker.

Compares README.md, docs/, pyproject.toml, env var docs, and Docker docs for
mismatched commands, versions, URLs, and undocumented env vars.

Exit code is always 0 (informational only).

Usage:
    python scripts/check-docs-drift.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"
DOCS_DIR = REPO_ROOT / "docs"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CONFIG_PY = REPO_ROOT / "src" / "docreview360" / "config.py"

# ── Helpers ───────────────────────────────────────────────────────────────────

findings: list[str] = []


def note(msg: str) -> None:
    findings.append(msg)
    print(f"  DRIFT: {msg}")


def ok(msg: str) -> None:
    print(f"  ok   : {msg}")


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("="*60)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def read_docs_all() -> str:
    """Concatenate all .md files under docs/."""
    parts: list[str] = []
    if DOCS_DIR.exists():
        for md in sorted(DOCS_DIR.rglob("*.md")):
            parts.append(md.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


# ── 1. Version check ──────────────────────────────────────────────────────────

def check_version() -> None:
    section("Version consistency")
    pyproject_text = read_text(PYPROJECT)
    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', pyproject_text, re.MULTILINE)
    if not m:
        note("Cannot parse version from pyproject.toml")
        return
    pkg_version = m.group(1)
    print(f"  pyproject.toml version: {pkg_version}")

    readme_text = read_text(README)
    docs_text = read_docs_all()

    # Look for version-like strings in README
    readme_versions = re.findall(r'v(\d+\.\d+(?:\.\d+)?)', readme_text)
    if readme_versions:
        unique = sorted(set(readme_versions))
        if pkg_version not in [f"{v}" for v in unique] and pkg_version not in readme_text:
            note(
                f"README.md does not mention package version {pkg_version}. "
                f"Found versions: {unique}"
            )
        else:
            ok(f"README.md references version {pkg_version}")
    else:
        note(f"README.md contains no version references matching v<N>.<N>")

    # Check CHANGELOG if it exists
    changelog = REPO_ROOT / "CHANGELOG.md"
    if changelog.exists():
        cl_text = changelog.read_text(encoding="utf-8", errors="replace")
        if pkg_version not in cl_text:
            note(f"CHANGELOG.md does not mention current version {pkg_version}")
        else:
            ok(f"CHANGELOG.md references version {pkg_version}")
    else:
        note("CHANGELOG.md does not exist — not yet created (checklist item 15)")


# ── 2. Python version ─────────────────────────────────────────────────────────

def check_python_version() -> None:
    section("Python version constraint")
    pyproject_text = read_text(PYPROJECT)
    m = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', pyproject_text)
    if not m:
        note("Cannot parse requires-python from pyproject.toml")
        return
    py_constraint = m.group(1)
    print(f"  pyproject.toml requires-python: {py_constraint}")

    claude_text = read_text(CLAUDE_MD)
    # CLAUDE.md says "Python 3.11–3.12; 3.13 not supported"
    if "3.12" in claude_text:
        ok("CLAUDE.md references Python 3.12")
    else:
        note("CLAUDE.md does not reference Python 3.12")

    if "3.13" in claude_text and "not supported" in claude_text:
        ok("CLAUDE.md notes Python 3.13 as not supported")
    elif "<3.13" in py_constraint:
        # Check README/docs mention of 3.13
        readme_text = read_text(README)
        docs_text = read_docs_all()
        combined = readme_text + docs_text
        if "3.13" in combined and "not supported" not in combined:
            note(
                "pyproject.toml excludes Python 3.13 (<3.13) but "
                "docs/README do not warn against it"
            )
        else:
            ok("Python 3.13 exclusion is consistent")


# ── 3. Port references ────────────────────────────────────────────────────────

def check_ports() -> None:
    section("Port references (8000 backend, 3000 frontend)")
    readme_text = read_text(README)
    docs_text = read_docs_all()
    claude_text = read_text(CLAUDE_MD)
    combined = readme_text + docs_text + claude_text

    for port, label in [("8000", "backend"), ("3000", "frontend")]:
        if port in combined:
            ok(f"Port {port} ({label}) mentioned in docs/README/CLAUDE.md")
        else:
            note(f"Port {port} ({label}) not found in README, docs/, or CLAUDE.md")

    # Warn if a different backend port is mentioned without 8000
    other_ports = re.findall(r':(\d{4,5})', combined)
    unusual = [p for p in set(other_ports) if p not in {"8000", "3000", "5432",
               "6379", "9200", "9090", "9091", "8080", "8443", "443", "80"}]
    if unusual:
        note(f"Unusual port(s) found in docs: {sorted(set(unusual))} — verify they are intentional")


# ── 4. Env vars documented ────────────────────────────────────────────────────

def check_env_vars() -> None:
    section("Env var documentation coverage")
    config_text = read_text(CONFIG_PY)

    # Extract env var names from _ENV_OVERRIDES dict and os.getenv() calls
    env_from_overrides = re.findall(r'"(DOCREVIEW360_[A-Z_]+)"', config_text)
    env_from_overrides += re.findall(r'"([A-Z_]+_URL)"', config_text)
    env_from_getenv = re.findall(r'os\.getenv\(["\']([A-Z_][A-Z0-9_]+)["\']', config_text)
    all_env_vars = sorted(set(env_from_overrides + env_from_getenv))

    docs_text = read_docs_all()
    readme_text = read_text(README)
    claude_text = read_text(CLAUDE_MD)
    combined = docs_text + readme_text + claude_text

    undocumented = [v for v in all_env_vars if v not in combined]
    if undocumented:
        note(
            f"{len(undocumented)} env var(s) from config.py not found in any doc: "
            + ", ".join(undocumented)
        )
    else:
        ok(f"All {len(all_env_vars)} env vars from config.py appear in docs")

    # Also check environment.py for additional env vars
    env_py = REPO_ROOT / "src" / "docreview360" / "environment.py"
    if env_py.exists():
        env_py_text = env_py.read_text(encoding="utf-8", errors="replace")
        extra = re.findall(r'os\.getenv\(["\']([A-Z_][A-Z0-9_]+)["\']', env_py_text)
        extra_undoc = [v for v in sorted(set(extra)) if v not in combined and v not in all_env_vars]
        if extra_undoc:
            note(
                f"{len(extra_undoc)} env var(s) from environment.py not found in docs: "
                + ", ".join(extra_undoc[:10])
                + (" ..." if len(extra_undoc) > 10 else "")
            )


# ── 5. Docker docs consistency ────────────────────────────────────────────────

def check_docker_docs() -> None:
    section("Docker documentation consistency")
    dockerfile = REPO_ROOT / "Dockerfile"
    compose = REPO_ROOT / "docker-compose.prod.yml"
    docs_text = read_docs_all()
    readme_text = read_text(README)

    if not dockerfile.exists():
        note("Dockerfile not found at repo root")
    else:
        ok("Dockerfile exists")
        df_text = dockerfile.read_text(encoding="utf-8", errors="replace")
        # Check Python base image version matches constraint
        m = re.search(r'FROM\s+python:(\d+\.\d+)', df_text)
        if m:
            docker_py = m.group(1)
            pyproject_text = read_text(PYPROJECT)
            if docker_py not in pyproject_text:
                note(
                    f"Dockerfile uses Python {docker_py} but pyproject.toml "
                    f"requires-python does not mention {docker_py}"
                )
            else:
                ok(f"Dockerfile Python version ({docker_py}) is consistent with pyproject.toml")

    if not compose.exists():
        note("docker-compose.prod.yml not found")
    else:
        ok("docker-compose.prod.yml exists")

    # Check docs mention Docker
    if "docker" in docs_text.lower() or "docker" in readme_text.lower():
        ok("Docker referenced in docs/README")
    else:
        note("No Docker references found in docs/ or README.md")


# ── 6. Install command consistency ───────────────────────────────────────────

def check_install_commands() -> None:
    section("Install command consistency")
    claude_text = read_text(CLAUDE_MD)
    readme_text = read_text(README)

    # CLAUDE.md uses `uv` for installs
    if "uv pip install" in claude_text:
        ok("CLAUDE.md uses uv pip install")
    else:
        note("CLAUDE.md does not reference 'uv pip install'")

    if "npm install" in claude_text:
        ok("CLAUDE.md references npm install for frontend")
    else:
        note("CLAUDE.md does not reference npm install")

    # Check if README also mentions a quick-start
    if "install" in readme_text.lower():
        ok("README.md contains install instructions")
    else:
        note("README.md has no install instructions — Quick Start section may be missing")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("DocReview360 Docs Drift Checker")
    print(f"Repo root: {REPO_ROOT}")

    check_version()
    check_python_version()
    check_ports()
    check_env_vars()
    check_docker_docs()
    check_install_commands()

    print(f"\n{'='*60}")
    if findings:
        print(f"SUMMARY: {len(findings)} drift finding(s) detected.")
        for i, f in enumerate(findings, 1):
            print(f"  {i}. {f}")
    else:
        print("SUMMARY: No drift detected. Documentation looks consistent.")
    print("="*60)
    # Always exit 0 (informational)
    sys.exit(0)


if __name__ == "__main__":
    main()
