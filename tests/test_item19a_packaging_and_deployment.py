# SPDX-License-Identifier: MIT
"""Item 19a / Item 152 / Item 160 — Packaging auditor and deployment drift checker tests.

Covers:
  - scripts/packaging-audit.py: exits 0, SUMMARY output, checks package-data,
    .dockerignore, dist/, placeholder scan reference
  - scripts/check-deployment-drift.py: exits 0, SUMMARY output, port checks,
    health check detection, env var consistency, image tag detection, Dockerfile
    security
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
PACKAGING_AUDIT = SCRIPTS_DIR / "packaging-audit.py"
DEPLOYMENT_DRIFT = SCRIPTS_DIR / "check-deployment-drift.py"


def run_script(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


# ---------------------------------------------------------------------------
# packaging-audit.py — basic contract
# ---------------------------------------------------------------------------

class TestPackagingAudit:
    def test_script_exists(self) -> None:
        assert PACKAGING_AUDIT.exists(), "scripts/packaging-audit.py not found"

    def test_exits_zero(self) -> None:
        result = run_script(PACKAGING_AUDIT)
        assert result.returncode == 0

    def test_prints_summary(self) -> None:
        result = run_script(PACKAGING_AUDIT)
        assert "SUMMARY" in result.stdout

    def test_checks_package_data(self) -> None:
        result = run_script(PACKAGING_AUDIT)
        combined = result.stdout + result.stderr
        assert "package-data" in combined.lower() or "pyproject" in combined.lower()

    def test_checks_dockerignore(self) -> None:
        result = run_script(PACKAGING_AUDIT)
        combined = result.stdout + result.stderr
        assert "dockerignore" in combined.lower() or ".dockerignore" in combined

    def test_references_placeholder_script(self) -> None:
        result = run_script(PACKAGING_AUDIT)
        assert "check-placeholders" in result.stdout

    def test_output_has_ok_or_warn_markers(self) -> None:
        result = run_script(PACKAGING_AUDIT)
        has_marker = ("ok   :" in result.stdout or "WARN :" in result.stdout)
        assert has_marker


# ---------------------------------------------------------------------------
# packaging-audit.py — source-level
# ---------------------------------------------------------------------------

class TestPackagingAuditSource:
    def _text(self) -> str:
        return PACKAGING_AUDIT.read_text(encoding="utf-8")

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in self._text()

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in self._text()

    def test_defines_junk_patterns(self) -> None:
        text = self._text()
        assert "JUNK_PATTERNS" in text
        assert "tests/" in text

    def test_checks_wildcard_package_data(self) -> None:
        text = self._text()
        assert "wildcard" in text.lower() or '"*"' in text

    def test_checks_dist_directory(self) -> None:
        text = self._text()
        assert "dist/" in text or "DIST_DIR" in text

    def test_check_dockerignore_function(self) -> None:
        text = self._text()
        assert "check_dockerignore" in text

    def test_check_package_data_function(self) -> None:
        text = self._text()
        assert "check_package_data" in text


# ---------------------------------------------------------------------------
# check-deployment-drift.py — basic contract
# ---------------------------------------------------------------------------

class TestDeploymentDrift:
    def test_script_exists(self) -> None:
        assert DEPLOYMENT_DRIFT.exists(), "scripts/check-deployment-drift.py not found"

    def test_exits_zero(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        assert result.returncode == 0

    def test_prints_summary(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        assert "SUMMARY" in result.stdout

    def test_checks_ports(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        combined = result.stdout + result.stderr
        assert "port" in combined.lower() or "8000" in combined

    def test_checks_health_endpoints(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        combined = result.stdout + result.stderr
        assert "health" in combined.lower()

    def test_checks_env_vars(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        combined = result.stdout + result.stderr
        assert "env" in combined.lower() or "SECRET" in combined or "DATABASE" in combined

    def test_checks_image_tags(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        combined = result.stdout + result.stderr
        assert "tag" in combined.lower() or "latest" in combined.lower() or "image" in combined.lower()

    def test_checks_dockerfile_security(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        combined = result.stdout + result.stderr
        assert "dockerfile" in combined.lower() or "Dockerfile" in combined

    def test_output_has_ok_or_drift_markers(self) -> None:
        result = run_script(DEPLOYMENT_DRIFT)
        has_marker = ("ok   :" in result.stdout or "DRIFT:" in result.stdout)
        assert has_marker


# ---------------------------------------------------------------------------
# check-deployment-drift.py — source-level
# ---------------------------------------------------------------------------

class TestDeploymentDriftSource:
    def _text(self) -> str:
        return DEPLOYMENT_DRIFT.read_text(encoding="utf-8")

    def test_spdx_header(self) -> None:
        assert "SPDX-License-Identifier: MIT" in self._text()

    def test_exits_zero_documented(self) -> None:
        assert "sys.exit(0)" in self._text()

    def test_check_ports_function(self) -> None:
        assert "check_ports" in self._text()

    def test_check_healthchecks_function(self) -> None:
        assert "check_healthchecks" in self._text()

    def test_check_env_vars_function(self) -> None:
        assert "check_env_vars" in self._text()

    def test_check_image_tags_function(self) -> None:
        assert "check_image_tags" in self._text()

    def test_check_dockerfile_security_function(self) -> None:
        assert "check_dockerfile_security" in self._text()

    def test_compares_multiple_files(self) -> None:
        text = self._text()
        # Should compare multiple files
        assert "Dockerfile" in text
        assert "docker-compose" in text
        assert "deployment.md" in text or "DEPLOYMENT_DOCS" in text

    def test_critical_env_vars_listed(self) -> None:
        text = self._text()
        assert "DOCREVIEW360_SECRET_KEY" in text
        assert "DATABASE_URL" in text

    def test_non_root_user_check(self) -> None:
        text = self._text()
        assert "non-root" in text or "USER" in text

    def test_healthcheck_directive_check(self) -> None:
        text = self._text()
        assert "HEALTHCHECK" in text
