# SPDX-License-Identifier: MIT
"""Item 178 — Security-defaults reviewer tests.

Covers:
  - scripts/security-defaults-review.py: exits 0, SUMMARY output
  - Eight check sections: JWT, lifetimes, OIDC/Keycloak, password, MFA, env defaults,
    LDAP/SAML, token revocation
  - Summary grouped by severity
  - Source-level checks for all helper functions
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SEC_REVIEW = SCRIPTS_DIR / "security-defaults-review.py"


def run_script() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SEC_REVIEW)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )


class TestSecurityDefaultsContract:
    def test_script_exists(self) -> None:
        assert SEC_REVIEW.exists(), "scripts/security-defaults-review.py not found"

    def test_exits_zero(self) -> None:
        result = run_script()
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"

    def test_prints_summary(self) -> None:
        result = run_script()
        assert "SUMMARY" in result.stdout

    def test_prints_repo_root(self) -> None:
        result = run_script()
        assert "Repo root" in result.stdout or "DocReview360" in result.stdout

    def test_covers_jwt(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "jwt" in combined.lower() or "JWT" in combined

    def test_covers_token_lifetimes(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "lifetime" in combined.lower() or "expire" in combined.lower() or "token" in combined.lower()

    def test_covers_oidc(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "oidc" in combined.lower() or "keycloak" in combined.lower()

    def test_covers_password_policy(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "password" in combined.lower()

    def test_covers_mfa(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "mfa" in combined.lower() or "totp" in combined.lower() or "otp" in combined.lower()

    def test_covers_env_defaults(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "env" in combined.lower() or "environment" in combined.lower()

    def test_covers_ldap_or_saml(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "ldap" in combined.lower() or "saml" in combined.lower()

    def test_covers_token_revocation(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        assert "revoc" in combined.lower() or "revoke" in combined.lower()

    def test_summary_has_severity_labels_or_clean(self) -> None:
        result = run_script()
        combined = result.stdout + result.stderr
        has_severity = any(
            s in combined
            for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "No actionable"]
        )
        assert has_severity


class TestSecurityDefaultsSource:
    def _text(self) -> str:
        return SEC_REVIEW.read_text(encoding="utf-8")

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in self._text()

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in self._text()

    def test_check_jwt_function(self) -> None:
        assert "check_jwt_secrets" in self._text()

    def test_check_token_lifetimes_function(self) -> None:
        assert "check_token_lifetimes" in self._text()

    def test_check_oidc_function(self) -> None:
        assert "check_oidc_keycloak" in self._text()

    def test_check_password_function(self) -> None:
        assert "check_password_policy" in self._text()

    def test_check_mfa_function(self) -> None:
        assert "check_mfa" in self._text()

    def test_check_env_defaults_function(self) -> None:
        assert "check_env_defaults" in self._text()

    def test_check_ldap_saml_function(self) -> None:
        assert "check_ldap_saml" in self._text()

    def test_check_token_revocation_function(self) -> None:
        assert "check_token_revocation" in self._text()

    def test_print_summary_function(self) -> None:
        assert "print_summary" in self._text()

    def test_severity_ordering(self) -> None:
        text = self._text()
        ci = text.find('"CRITICAL"')
        hi = text.find('"HIGH"')
        if ci >= 0 and hi >= 0:
            assert ci < hi, "CRITICAL should come before HIGH in severity ordering"

    def test_note_function(self) -> None:
        assert "def note(" in self._text()

    def test_ok_function(self) -> None:
        assert "def ok(" in self._text()

    def test_section_function(self) -> None:
        assert "def section(" in self._text()

    def test_keycloak_reference(self) -> None:
        text = self._text()
        assert "keycloak" in text.lower() or "Keycloak" in text

    def test_pkce_reference(self) -> None:
        text = self._text()
        assert "PKCE" in text or "pkce" in text.lower() or "code_verifier" in text

    def test_graceful_missing_file(self) -> None:
        text = self._text()
        assert "not found" in text or "not exist" in text or ".exists()" in text
