"""CI gate enforcement tests."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


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


def test_ci_jobs_have_explicit_timeouts() -> None:
    """Every required CI job must fail boundedly instead of hanging indefinitely."""

    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert jobs
    for job_name, job in jobs.items():
        timeout = job.get("timeout-minutes")
        assert isinstance(timeout, int), f"{job_name} is missing timeout-minutes"
        assert 1 <= timeout <= 120, f"{job_name} timeout should stay bounded"
