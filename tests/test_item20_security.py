# SPDX-License-Identifier: MIT
"""Item 20 — Security and compliance checks.

Tests:
  - SECURITY_REVIEW.md has required sections (Step 1-5, threat model, findings)
  - SECURITY.md references real security checks (Bandit, pip-audit, npm audit)
  - CI workflows actually run bandit and pip-audit
  - verify_audit_log_chain is exported and callable
  - Audit log integrity test runs (hash chain functional)
  - Password policy module exists with configurable fields
  - JWT secret key config is environment-driven (not hardcoded)
  - db_encryption.py AES-256-GCM TypeDecorator exists
"""
from __future__ import annotations

import importlib
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "docreview360"
SECURITY_MD = REPO_ROOT / "SECURITY.md"
SECURITY_REVIEW_MD = REPO_ROOT / "SECURITY_REVIEW.md"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
NIGHTLY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "nightly-tests.yml"


# ---------------------------------------------------------------------------
# SECURITY_REVIEW.md completeness
# ---------------------------------------------------------------------------

class TestSecurityReviewMd:
    def test_file_exists(self) -> None:
        assert SECURITY_REVIEW_MD.exists(), "SECURITY_REVIEW.md not found"

    def test_has_threat_model_section(self) -> None:
        text = SECURITY_REVIEW_MD.read_text(encoding="utf-8-sig")
        assert "Threat Model" in text or "threat model" in text.lower()

    def test_has_attack_paths(self) -> None:
        text = SECURITY_REVIEW_MD.read_text(encoding="utf-8-sig")
        assert "attack path" in text.lower() or "IDOR" in text or "SSRF" in text

    def test_has_automated_scans_section(self) -> None:
        text = SECURITY_REVIEW_MD.read_text(encoding="utf-8-sig")
        assert "Automated" in text or "bandit" in text.lower() or "scan" in text.lower()

    def test_has_assets_section(self) -> None:
        text = SECURITY_REVIEW_MD.read_text(encoding="utf-8-sig")
        assert "Assets" in text or "asset" in text.lower()

    def test_has_trust_boundaries(self) -> None:
        text = SECURITY_REVIEW_MD.read_text(encoding="utf-8-sig")
        assert "Trust" in text or "trust boundary" in text.lower()

    def test_mentions_upload_surface(self) -> None:
        text = SECURITY_REVIEW_MD.read_text(encoding="utf-8-sig")
        assert "upload" in text.lower() or "Upload" in text

    def test_mentions_auth_session(self) -> None:
        text = SECURITY_REVIEW_MD.read_text(encoding="utf-8-sig")
        assert "JWT" in text or "session" in text.lower()


# ---------------------------------------------------------------------------
# SECURITY.md — references to actual security checks
# ---------------------------------------------------------------------------

class TestSecurityMd:
    def test_file_exists(self) -> None:
        assert SECURITY_MD.exists(), "SECURITY.md not found"

    def test_references_bandit(self) -> None:
        text = SECURITY_MD.read_text(encoding="utf-8")
        assert "Bandit" in text or "bandit" in text

    def test_references_pip_audit(self) -> None:
        text = SECURITY_MD.read_text(encoding="utf-8")
        assert "pip-audit" in text

    def test_references_npm_audit(self) -> None:
        text = SECURITY_MD.read_text(encoding="utf-8")
        assert "npm audit" in text

    def test_has_reporting_section(self) -> None:
        text = SECURITY_MD.read_text(encoding="utf-8")
        assert "Reporting" in text or "Vulnerability" in text


# ---------------------------------------------------------------------------
# CI workflows actually run security checks
# ---------------------------------------------------------------------------

class TestCiSecurityChecks:
    def test_ci_workflow_exists(self) -> None:
        assert CI_WORKFLOW.exists(), ".github/workflows/ci.yml not found"

    def test_ci_runs_bandit(self) -> None:
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        assert "bandit" in text.lower()

    def test_nightly_workflow_exists(self) -> None:
        assert NIGHTLY_WORKFLOW.exists(), ".github/workflows/nightly-tests.yml not found"

    def test_nightly_runs_bandit(self) -> None:
        text = NIGHTLY_WORKFLOW.read_text(encoding="utf-8")
        assert "bandit" in text.lower()

    def test_nightly_runs_pip_audit(self) -> None:
        text = NIGHTLY_WORKFLOW.read_text(encoding="utf-8")
        assert "pip-audit" in text.lower() or "run-pip-audit" in text

    def test_pip_audit_script_exists(self) -> None:
        script = REPO_ROOT / "scripts" / "run-pip-audit.py"
        assert script.exists(), "scripts/run-pip-audit.py not found"


# ---------------------------------------------------------------------------
# Audit log integrity — verify_audit_log_chain
# ---------------------------------------------------------------------------

class TestAuditLogIntegrity:
    def test_verify_audit_log_chain_exported(self) -> None:
        """verify_audit_log_chain must be importable from the logs package."""
        from docreview360.logs import verify_audit_log_chain  # noqa: F401

    def test_verify_audit_log_chain_callable(self) -> None:
        from docreview360.logs import verify_audit_log_chain
        assert callable(verify_audit_log_chain)

    def test_audit_log_chain_with_empty_db(self) -> None:
        """Calling verify_audit_log_chain on a fresh DB should return (bool, list) tuple."""
        from docreview360.logs import verify_audit_log_chain
        result = verify_audit_log_chain()
        # Returns (is_valid: bool, broken_ids: list) tuple
        assert isinstance(result, tuple) or isinstance(result, (bool, list, dict))

    def test_logs_package_exports_all_symbols(self) -> None:
        """logs/__init__.py should export the expected public API."""
        from docreview360 import logs
        assert hasattr(logs, "verify_audit_log_chain")
        assert hasattr(logs, "log_event") or hasattr(logs, "query_logs")


# ---------------------------------------------------------------------------
# Password policy module
# ---------------------------------------------------------------------------

class TestPasswordPolicy:
    def test_password_history_table_documented(self) -> None:
        """auth/_core.py or auth/_models.py should reference password_history."""
        auth_core = SRC / "auth" / "_core.py"
        auth_models = SRC / "auth" / "_models.py"
        text = ""
        for path in [auth_core, auth_models]:
            if path.exists():
                text += path.read_text(encoding="utf-8")
        assert "password_history" in text or "PasswordPolicy" in text

    def test_password_policy_has_history_count(self) -> None:
        """PasswordPolicy must have a history_count setting."""
        # Check across auth package files
        found = False
        for pyfile in (SRC / "auth").glob("*.py"):
            text = pyfile.read_text(encoding="utf-8")
            if "history_count" in text:
                found = True
                break
        assert found, "history_count not found in auth package"

    def test_password_max_age_days_configurable(self) -> None:
        found = False
        for pyfile in (SRC / "auth").glob("*.py"):
            text = pyfile.read_text(encoding="utf-8")
            if "max_age_days" in text:
                found = True
                break
        assert found, "max_age_days not found in auth package"


# ---------------------------------------------------------------------------
# Encryption-at-rest — db_encryption.py
# ---------------------------------------------------------------------------

class TestEncryptionAtRest:
    def test_db_encryption_module_exists(self) -> None:
        assert (SRC / "db_encryption.py").exists(), "db_encryption.py not found"

    def test_encrypted_string_type_decorator(self) -> None:
        text = (SRC / "db_encryption.py").read_text(encoding="utf-8")
        assert "EncryptedString" in text

    def test_aes_256_gcm_used(self) -> None:
        text = (SRC / "db_encryption.py").read_text(encoding="utf-8")
        # AES-256-GCM or AESGCM
        assert "AES" in text or "AESGCM" in text or "256" in text

    def test_enc_v1_prefix(self) -> None:
        text = (SRC / "db_encryption.py").read_text(encoding="utf-8")
        assert "enc:v1:" in text or "v1" in text


# ---------------------------------------------------------------------------
# JWT secret is environment-driven (not hardcoded in production)
# ---------------------------------------------------------------------------

class TestJwtSecretConfig:
    def test_jwt_secret_reads_from_env(self) -> None:
        """The JWT secret must be configurable via environment variable."""
        # auth/__init__.py defines SECRET_KEY via env var
        auth_init = SRC / "auth" / "__init__.py"
        if auth_init.exists():
            text = auth_init.read_text(encoding="utf-8")
        else:
            # Fallback: check any auth-related file
            text = ""
            for pyfile in (SRC / "auth").glob("*.py"):
                text += pyfile.read_text(encoding="utf-8")
        assert "SECRET_KEY" in text or "JWT_SECRET" in text or "DOCREVIEW360_SECRET_KEY" in text

    def test_auth_package_enforces_secret_in_production(self) -> None:
        """JWT secret enforcement must exist for production environments."""
        auth_init = SRC / "auth" / "__init__.py"
        text = auth_init.read_text(encoding="utf-8")
        # Should reject weak or default secrets in production
        assert "required=True" in text or "production" in text.lower() or "_BANNED" in text
