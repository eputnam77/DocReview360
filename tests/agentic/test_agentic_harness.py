from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentic.agents import OrchestratorAgent
from agentic.bug_logger import BugLoggerAgent
from agentic.models import Actor, AgenticRunConfig, BrowserRunConfig, BugReport, ScenarioState
from agentic.runner import run_agentic_suite
from docreview360 import auth, rbac
from docreview360.api import app


def _configure_auth_stores(tmp_path: Path) -> None:
    auth.configure_user_repository(tmp_path / "agentic-users.db")
    rbac.configure_role_repository(tmp_path / "agentic-roles.db")
    rbac.reset_role_assignments()


def test_agentic_document_review_scenario_passes(tmp_path: Path) -> None:
    _configure_auth_stores(tmp_path)

    results = run_agentic_suite(run_id="pytest", bug_report_dir=tmp_path / "bugs")

    assert len(results) == 1
    result = results[0]
    assert result.passed, result.bug_reports[0].actual if result.bug_reports else "unknown failure"
    assert result.state.project_id == "agentic-pytest"
    assert result.state.document_id is not None
    assert result.state.approval_ids
    assert result.state.comment_ids
    assert not list((tmp_path / "bugs").glob("*.json"))


def test_orchestrator_records_bug_report_when_scenario_fails(tmp_path: Path) -> None:
    _configure_auth_stores(tmp_path)
    config = AgenticRunConfig(run_id="failure", bug_report_dir=tmp_path / "bugs")
    orchestrator = OrchestratorAgent(client=TestClient(app), config=config)

    def broken_scenario(inner_orchestrator: OrchestratorAgent, state: ScenarioState) -> None:
        actor = Actor(username="agentic-admin", roles=("admin",), kind="admin_edge")
        session = inner_orchestrator.seed_actor(actor, state)
        session.request("GET", "/projects/does-not-exist", expected=200)

    result = orchestrator.run(name="broken", scenario=broken_scenario)

    assert not result.passed
    reports = list((tmp_path / "bugs").glob("bug-*.json"))
    assert len(reports) == 1
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["run_id"] == "failure"
    assert payload["severity"] == "high"
    assert payload["api_traces"][0]["actual_status"] == 404


def test_agentic_run_config_rejects_invalid_guardrails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run_id"):
        AgenticRunConfig(run_id="", bug_report_dir=tmp_path)
    with pytest.raises(ValueError, match="max_steps"):
        AgenticRunConfig(run_id="x", bug_report_dir=tmp_path, max_steps=0)
    with pytest.raises(ValueError, match="uppercase"):
        AgenticRunConfig(run_id="x", bug_report_dir=tmp_path, allowed_methods=("get",))


def test_browser_run_config_validates_watchable_urls() -> None:
    config = BrowserRunConfig(
        frontend_url="http://localhost:3000/",
        backend_url="http://localhost:8000/",
    )

    assert config.normalized_frontend_url == "http://localhost:3000"
    assert config.normalized_backend_url == "http://localhost:8000"
    assert config.headed is True

    with pytest.raises(ValueError, match="frontend_url"):
        BrowserRunConfig(frontend_url="localhost:3000", backend_url="http://localhost:8000")


def test_bug_logger_writes_structured_json(tmp_path: Path) -> None:
    report = BugReport(
        id="bug-test",
        run_id="run-test",
        title="Example failure",
        severity="medium",
        expected="Workflow succeeds",
        actual="Workflow failed",
        repro_steps=("Create project", "Approve document"),
        api_traces=(),
    )

    path = BugLoggerAgent(tmp_path).record(report)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["id"] == "bug-test"
    assert payload["repro_steps"] == ["Create project", "Approve document"]
    assert payload["created_at"]
