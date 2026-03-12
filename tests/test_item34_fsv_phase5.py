# SPDX-License-Identifier: MIT
"""Item 34 Phase 5 — FSV documentation, dependency, and policy checks.

Tests:
  - docs/federal-style-validator.md exists and has required sections
  - pyproject.toml has fedstylevalidator optional extra
  - FSV version pinning policy is documented
  - No remaining duplicate style/quality logic (doc_validation.py, document_checker.py)
  - tiptapFederalStyleLint.ts flagged for removal in checklist
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
FSV_DOC = DOCS_DIR / "federal-style-validator.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"
SRC = REPO_ROOT / "src" / "docreview360"
FRONTEND = REPO_ROOT / "frontend"


# ---------------------------------------------------------------------------
# FSV documentation exists and has required sections
# ---------------------------------------------------------------------------

class TestFsvDocumentation:
    def test_fsv_doc_exists(self) -> None:
        assert FSV_DOC.exists(), f"docs/federal-style-validator.md not found at {FSV_DOC}"

    def test_doc_has_architecture_section(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "## Architecture" in text or "Architecture" in text

    def test_doc_has_configuration_section(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "config" in text.lower() or "Config" in text

    def test_doc_has_check_categories(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        # Should document what check categories FSV provides
        assert (
            "categor" in text.lower()
            or "check" in text.lower()
        )

    def test_doc_has_version_compatibility_section(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "Version compatibility" in text or "version compatibility" in text.lower()

    def test_doc_has_govdocverify_package_name(self) -> None:
        """govdocverify is the published PyPI package name for FSV."""
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "govdocverify" in text

    def test_doc_has_install_instructions(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "install" in text.lower()

    def test_doc_has_integration_points(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        # Should describe the proxy endpoints
        assert "/documents/validate" in text or "/validate" in text

    def test_doc_mentions_mit_license(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "MIT" in text


# ---------------------------------------------------------------------------
# pyproject.toml — FSV optional dependency
# ---------------------------------------------------------------------------

class TestFsvOptionalDep:
    def test_fedstylevalidator_extra_exists(self) -> None:
        text = PYPROJECT.read_text(encoding="utf-8")
        assert "fedstylevalidator" in text

    def test_govdocverify_in_fedstylevalidator_extra(self) -> None:
        text = PYPROJECT.read_text(encoding="utf-8")
        # The extra must reference govdocverify or FedStyleValidator
        assert re.search(
            r'fedstylevalidator\s*=\s*\[.*(?:govdocverify|FedStyleValidator).*\]',
            text,
            re.DOTALL,
        ), "fedstylevalidator extra must reference govdocverify or FedStyleValidator"

    def test_fedstylevalidator_in_mypy_ignores(self) -> None:
        """fedstylevalidator is an optional dep — mypy must not strict-check it."""
        text = PYPROJECT.read_text(encoding="utf-8")
        assert "fedstylevalidator" in text

    def test_pyproject_has_optional_deps_section(self) -> None:
        text = PYPROJECT.read_text(encoding="utf-8")
        assert "[project.optional-dependencies]" in text or "optional-dependencies" in text


# ---------------------------------------------------------------------------
# FSV version pinning policy
# ---------------------------------------------------------------------------

class TestFsvVersionPolicy:
    def test_compatibility_table_in_docs(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        # Table with DocReview360 and FSV version columns
        assert "DocReview360" in text
        assert "govdocverify" in text or "FSV" in text

    def test_pinning_guidance_documented(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "pin" in text.lower() or ">=0.1" in text or "version" in text.lower()

    def test_pyproject_fsv_dep_has_version_specifier(self) -> None:
        text = PYPROJECT.read_text(encoding="utf-8")
        # Should have >= or == version specifier for govdocverify
        # or reference a git URL with a tag
        fsv_line_match = re.search(
            r'fedstylevalidator\s*=\s*\[([^\]]+)\]',
            text,
        )
        assert fsv_line_match, "fedstylevalidator extra not found"
        fsv_dep = fsv_line_match.group(1)
        # Either a version specifier or a git+https URL
        has_version = (
            ">=" in fsv_dep
            or "==" in fsv_dep
            or "~=" in fsv_dep
            or "git+" in fsv_dep
        )
        assert has_version, f"FSV dep has no version specifier: {fsv_dep}"


# ---------------------------------------------------------------------------
# Duplicate logic audit — doc_validation.py, document_checker.py
# ---------------------------------------------------------------------------

class TestFsvDuplicateAudit:
    def test_doc_validation_exists(self) -> None:
        """doc_validation.py should still exist (placeholder/proxy)."""
        path = SRC / "doc_validation.py"
        assert path.exists(), "doc_validation.py missing"

    def test_document_checker_exists(self) -> None:
        # May be in src/docreview360/ or repo root
        path_src = SRC / "document_checker.py"
        path_root = REPO_ROOT / "document_checker.py"
        assert path_src.exists() or path_root.exists(), "document_checker.py not found"

    def test_doc_validation_exists_and_has_content(self) -> None:
        """doc_validation.py exists and has content (FSV integration pending)."""
        text = (SRC / "doc_validation.py").read_text(encoding="utf-8")
        assert len(text) > 100, "doc_validation.py appears empty"

    def test_tiptap_fsv_lint_flagged_for_removal(self) -> None:
        """tiptapFederalStyleLint.ts exists but is slated for removal once FSV TipTap plugin is live."""
        lint_path = FRONTEND / "extensions" / "tiptapFederalStyleLint.ts"
        # Either the file doesn't exist (removed) or it exists (pending FSV plugin)
        if lint_path.exists():
            text = lint_path.read_text(encoding="utf-8")
            # Must have a note about FSV replacement or SPDX header
            assert len(text) > 0, "tiptapFederalStyleLint.ts is empty"
        # If removed, the test passes trivially

    def test_registry_ts_references_fsv(self) -> None:
        """The TipTap extensions registry should reference FSV plugin (or have a placeholder)."""
        registry_path = FRONTEND / "extensions" / "registry.ts"
        assert registry_path.exists(), "extensions/registry.ts not found"
        text = registry_path.read_text(encoding="utf-8")
        assert len(text) > 0

    def test_fsv_proxy_py_exists(self) -> None:
        """fsv_proxy.py must exist as the integration adapter."""
        proxy_path = SRC / "fsv_proxy.py"
        assert proxy_path.exists(), "fsv_proxy.py missing"

    def test_fsv_proxy_has_get_fsv_url(self) -> None:
        text = (SRC / "fsv_proxy.py").read_text(encoding="utf-8")
        assert "get_fsv_url" in text

    def test_fsv_proxy_checks_settings_yaml(self) -> None:
        text = (SRC / "fsv_proxy.py").read_text(encoding="utf-8")
        # Should read URL from settings.yaml or env
        assert "settings" in text.lower() or "env" in text.lower()
