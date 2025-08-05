"""CI gate enforcement tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = (ROOT / ".dev" / "AGENTS.md").read_text(encoding='utf-8')


def test_coverage_threshold_present() -> None:
    assert "--cov-fail-under=90" in AGENTS


def test_mutation_score_present() -> None:
    assert "mutmut run" in AGENTS


def test_playwright_coverage_present() -> None:
    assert "pytest -q -m e2e" in AGENTS


def test_trivy_scan_present() -> None:
    assert "trivy fs" in AGENTS


def test_terraform_templates_exist() -> None:
    assert (ROOT / "iac" / "eks.tf").exists()
