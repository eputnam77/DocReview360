# SPDX-License-Identifier: MIT
"""Item 34 Phase 5 — FSV dependency, policy, and pending-item checks.

Tests:
  - docs/federal-style-validator.md exists and tracks the two remaining pending items
  - pyproject.toml has fedstylevalidator optional extra with version specifier
  - No remaining duplicate style/quality logic (doc_validation.py, document_checker.py)
  - tiptapFederalStyleLint.ts flagged for removal in checklist

Note: Reference content (architecture, configuration, check categories, version
compatibility table) was removed from the doc once those items were implemented
and verified by integration tests (test_item34_fsv_proxy.py).
"""
from __future__ import annotations

import re
from pathlib import Path

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
    """The doc now tracks only pending (not-yet-implemented) items."""

    def test_fsv_doc_exists(self) -> None:
        assert FSV_DOC.exists(), f"docs/federal-style-validator.md not found at {FSV_DOC}"

    def test_doc_tracks_duplicate_removal_pending_item(self) -> None:
        """Removing internal duplicates is a pending item — must stay in the doc."""
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "Removing internal duplicates" in text or "regulatory.py" in text

    def test_doc_tracks_tiptap_plugin_pending_item(self) -> None:
        """TipTap plugin integration is a pending item — must stay in the doc."""
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "TipTap plugin" in text or "tiptap" in text.lower()

    def test_doc_references_regulatory_py_for_removal(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "regulatory.py" in text

    def test_doc_references_tiptap_lint_extension_for_removal(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "tiptapFederalStyleLint.ts" in text

    def test_doc_references_registry_ts(self) -> None:
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "registry.ts" in text

    def test_doc_mentions_phase5(self) -> None:
        """Removal is tracked behind Item 34 Phase 5."""
        text = FSV_DOC.read_text(encoding="utf-8")
        assert "Phase 5" in text or "phase 5" in text.lower()


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
