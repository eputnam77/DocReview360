# SPDX-License-Identifier: MIT
"""Packaging and platform documentation tests.

Covers:
  - MANIFEST.in correctness (tests excluded, runtime included)
  - pyproject.toml package-data (no broad wildcard)
  - docs/supported-platforms.md accuracy
  - docs/adr/0001-core-architecture.md existence and accuracy
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
MANIFEST = REPO_ROOT / "MANIFEST.in"
PLATFORMS_DOC = REPO_ROOT / "docs" / "supported-platforms.md"
ADR_DOC = REPO_ROOT / "docs" / "adr" / "0001-core-architecture.md"


class TestManifestIn:
    def test_manifest_exists(self) -> None:
        assert MANIFEST.exists(), "MANIFEST.in not found"

    def test_prune_tests(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert "prune tests" in text

    def test_prune_dev(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert "prune .dev" in text

    def test_prune_frontend(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert "prune frontend" in text

    def test_prune_scripts(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert "prune scripts" in text

    def test_includes_readme(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert "README.md" in text or "include README" in text

    def test_includes_license(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert "LICENSE" in text

    def test_excludes_env_files(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert ".env" in text or "global-exclude .env" in text

    def test_excludes_pyc(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        assert "*.pyc" in text or "__pycache__" in text


class TestPyprojectPackageData:
    def _text(self) -> str:
        return PYPROJECT.read_text(encoding="utf-8")

    def test_pyproject_exists(self) -> None:
        assert PYPROJECT.exists()

    def test_no_broad_wildcard_rule(self) -> None:
        text = self._text()
        # The old broad wildcard `"*" = [...]` should no longer exist
        assert '"*"' not in text or (
            '"*"' in text
            and "*.txt" not in text.split('"*"')[1].split("\n")[0]
        )

    def test_py_typed_marker(self) -> None:
        text = self._text()
        assert "py.typed" in text

    def test_explicit_docreview360_data(self) -> None:
        text = self._text()
        assert '"docreview360"' in text

    def test_tests_excluded_from_packages(self) -> None:
        text = self._text()
        # packages.find must exclude tests
        assert 'exclude = ["tests*"' in text or 'exclude = ["tests' in text

    def test_ml_assets_included(self) -> None:
        text = self._text()
        assert "ml" in text.lower() and (".onnx" in text or "onnx" in text.lower())


class TestSupportedPlatformsDoc:
    def _text(self) -> str:
        return PLATFORMS_DOC.read_text(encoding="utf-8")

    def test_doc_exists(self) -> None:
        assert PLATFORMS_DOC.exists(), "docs/supported-platforms.md not found"

    def test_python_versions_documented(self) -> None:
        text = self._text()
        assert "3.12" in text and "3.11" in text

    def test_python_313_not_supported(self) -> None:
        text = self._text()
        assert "3.13" in text
        # Must say it's not supported
        assert "not supported" in text.lower() or "Not supported" in text

    def test_node_version_documented(self) -> None:
        text = self._text()
        assert "18" in text or "20" in text or "Node" in text

    def test_linux_supported(self) -> None:
        text = self._text()
        assert "Linux" in text or "linux" in text.lower()

    def test_macos_supported(self) -> None:
        text = self._text()
        assert "macOS" in text or "Mac" in text

    def test_windows_supported(self) -> None:
        text = self._text()
        assert "Windows" in text

    def test_docker_supported(self) -> None:
        text = self._text()
        assert "Docker" in text or "docker" in text.lower()

    def test_raspberry_pi_documented(self) -> None:
        text = self._text()
        assert "Raspberry Pi" in text or "raspberry" in text.lower()

    def test_sqlite_documented(self) -> None:
        text = self._text()
        assert "SQLite" in text

    def test_kubernetes_documented(self) -> None:
        text = self._text()
        assert "Kubernetes" in text or "k8s" in text.lower() or "Helm" in text


class TestADR0001:
    def _text(self) -> str:
        return ADR_DOC.read_text(encoding="utf-8")

    def test_adr_exists(self) -> None:
        assert ADR_DOC.exists(), "docs/adr/0001-core-architecture.md not found"

    def test_status_accepted(self) -> None:
        assert "Accepted" in self._text()

    def test_fastapi_mentioned(self) -> None:
        assert "FastAPI" in self._text()

    def test_sqlalchemy_or_sqlite_mentioned(self) -> None:
        text = self._text()
        assert "SQLite" in text or "SQLAlchemy" in text

    def test_auth_mentioned(self) -> None:
        text = self._text()
        assert "JWT" in text or "auth" in text.lower()

    def test_sub_router_architecture(self) -> None:
        text = self._text()
        assert "sub-router" in text.lower() or "router" in text.lower()

    def test_storage_layout_section(self) -> None:
        text = self._text()
        assert "src/docreview360" in text or "Storage Layout" in text

    def test_consequences_section(self) -> None:
        assert "Consequences" in self._text()

    def test_alternatives_section(self) -> None:
        assert "Alternative" in self._text()
