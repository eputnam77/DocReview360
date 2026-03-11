from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PAGES = REPO_ROOT / "frontend" / "pages"


def _project_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_dockerfile_uses_mit_license_label() -> None:
    dockerfile = _project_file("Dockerfile")
    assert 'org.opencontainers.image.licenses="MIT"' in dockerfile


def test_dockerignore_excludes_release_junk() -> None:
    dockerignore = _project_file(".dockerignore")
    required_entries = [
        ".git/",
        ".github/",
        "docs/",
        "tests/",
        "dist/",
        "build/",
        ".venv/",
        "frontend/node_modules/",
        ".coverage",
        ".coverage.*",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        ".hypothesis/",
        ".e2e-debug/",
        ".e2e-debug-webpack/",
        ".pytest_tmp/",
        ".tmp/",
        "docreview360.db",
        "docreview360_roles.db",
        "docreview360_users.db",
        "search_state.db",
        "worker_state.json",
        "workflow_templates.json",
        "email_templates.json",
        "template_store.json",
    ]
    for entry in required_entries:
        assert entry in dockerignore


def test_gitignore_covers_local_release_artifacts() -> None:
    gitignore = _project_file(".gitignore")
    required_entries = [
        ".e2e-debug/",
        ".e2e-debug-webpack/",
        ".pytest_tmp/",
        "worker_state.json",
        "workflow_templates.json",
        "workflow_templates.json.lock",
        "email_templates.json",
        "email_templates.json.lock",
        "template_store.json",
        "template_store.json.lock",
        "docreview360_roles.db",
        "docreview360_users.db",
        "search_state.db",
        "frontend/workflow_templates.json",
    ]
    assert "*.db" in gitignore or "docreview360.db" in gitignore
    for entry in required_entries:
        assert entry in gitignore


def test_workflow_template_file_env_var_removed_from_docs_and_examples() -> None:
    assert "DOCREVIEW360_WORKFLOW_TEMPLATES_FILE" not in _project_file(".env.example")
    assert "DOCREVIEW360_WORKFLOW_TEMPLATES_FILE" not in _project_file("README.md")
    assert "DOCREVIEW360_WORKFLOW_TEMPLATES_FILE" not in _project_file(
        "src/docreview360.egg-info/PKG-INFO"
    )


def test_protected_frontend_pages_do_not_use_raw_fetch() -> None:
    violations: list[str] = []
    for path in FRONTEND_PAGES.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        relative = path.relative_to(FRONTEND_PAGES)
        if relative.parts and relative.parts[0] == "api":
            continue
        if relative == Path("login.tsx"):
            continue
        if re.search(r"\bfetch\s*\(", path.read_text(encoding="utf-8")):
            violations.append(str(relative))
    assert violations == []
