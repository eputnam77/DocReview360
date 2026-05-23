from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient

from docreview360 import auth, rbac

from ..api_client import ActorSession
from ..bug_logger import BugLoggerAgent
from ..models import (
    Actor,
    AgenticRunConfig,
    BugReport,
    ScenarioResult,
    ScenarioState,
)

Scenario = Callable[["OrchestratorAgent", ScenarioState], None]


class OrchestratorAgent:
    """Coordinates seeded actors, guarded scenarios, and bug logging."""

    def __init__(self, *, client: TestClient, config: AgenticRunConfig) -> None:
        self.client = client
        self.config = config
        self.bug_logger = BugLoggerAgent(config.bug_report_dir)
        self._sessions: dict[str, ActorSession] = {}

    def seed_actor(self, actor: Actor, state: ScenarioState) -> ActorSession:
        repo = auth.USER_REPOSITORY
        if repo.get_user(actor.username) is None:
            repo.create_user(actor.username, actor.password, active=actor.active)
        else:
            repo.set_active(actor.username, actor.active)
        rbac.set_user_roles(
            actor.username,
            list(actor.roles),
            actor="agentic-harness",
            context={"run_id": self.config.run_id},
        )
        session = ActorSession(actor=actor, client=self.client, state=state)
        self._sessions[actor.username] = session
        return session

    def run(self, *, name: str, scenario: Scenario) -> ScenarioResult:
        state = ScenarioState(run_id=self.config.run_id)
        bug_reports: list[BugReport] = []
        try:
            scenario(self, state)
            self._enforce_step_budget(state)
        except Exception as exc:
            report = self._build_bug_report(name=name, state=state, error=exc)
            self.bug_logger.record(report)
            bug_reports.append(report)
        return ScenarioResult(name=name, state=state, bug_reports=bug_reports)

    def session_for(self, username: str) -> ActorSession:
        try:
            return self._sessions[username]
        except KeyError as exc:
            raise ValueError(f"actor {username!r} has not been seeded") from exc

    def _enforce_step_budget(self, state: ScenarioState) -> None:
        if len(state.traces) > self.config.max_steps:
            raise RuntimeError(
                f"scenario used {len(state.traces)} API steps; max_steps is {self.config.max_steps}"
            )

    def _build_bug_report(self, *, name: str, state: ScenarioState, error: Exception) -> BugReport:
        return BugReport(
            id=f"bug-{uuid4().hex[:12]}",
            run_id=self.config.run_id,
            title=f"{name} failed: {type(error).__name__}",
            severity="high",
            expected=f"Scenario {name} should complete within guarded API behavior.",
            actual=str(error),
            repro_steps=tuple(
                f"{trace.actor}: {trace.method} {trace.path} -> {trace.actual_status}"
                for trace in state.traces
            )
            or ("Run the scenario before the first API trace.",),
            api_traces=tuple(state.traces),
        )
