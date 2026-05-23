from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

AgentKind = Literal["orchestrator", "creator", "reviewer", "admin_edge", "fixer"]
BugSeverity = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class Actor:
    """A seeded test user and the roles they should have."""

    username: str
    roles: tuple[str, ...]
    kind: AgentKind
    password: str = "Password!1234"
    active: bool = True


@dataclass(frozen=True)
class AgenticRunConfig:
    """Runtime guardrails for a harness run."""

    run_id: str
    bug_report_dir: Path
    max_steps: int = 100
    allowed_methods: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE")
    allow_ui: bool = False

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        invalid = [method for method in self.allowed_methods if method.upper() != method]
        if invalid:
            raise ValueError(f"allowed_methods must be uppercase HTTP verbs: {invalid}")


@dataclass(frozen=True)
class BrowserRunConfig:
    """Configuration for a watchable browser-driven agent run."""

    frontend_url: str
    backend_url: str
    headed: bool = True
    slow_mo_ms: int = 400
    timeout_ms: int = 30_000
    admin_username: str = "bob"
    admin_password: str = "password"
    reviewer_username: str = "agentic-browser-reviewer"
    reviewer_password: str = "Password!1234"

    def __post_init__(self) -> None:
        _validate_http_url(self.frontend_url, "frontend_url")
        _validate_http_url(self.backend_url, "backend_url")
        if self.slow_mo_ms < 0:
            raise ValueError("slow_mo_ms must be zero or greater")
        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be at least 1")
        if not self.admin_username.strip():
            raise ValueError("admin_username must not be blank")
        if not self.reviewer_username.strip():
            raise ValueError("reviewer_username must not be blank")

    @property
    def normalized_frontend_url(self) -> str:
        return self.frontend_url.rstrip("/")

    @property
    def normalized_backend_url(self) -> str:
        return self.backend_url.rstrip("/")


def _validate_http_url(value: str, field_name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute http(s) URL")


@dataclass
class ApiTrace:
    """A compact record of one API interaction."""

    actor: str
    method: str
    path: str
    expected_statuses: tuple[int, ...]
    actual_status: int
    request_json: dict[str, Any] | list[Any] | None = None
    response_json: Any | None = None

    @property
    def ok(self) -> bool:
        return self.actual_status in self.expected_statuses


@dataclass
class ScenarioState:
    """Shared state passed among agents during a scenario."""

    run_id: str
    project_id: str | None = None
    workflow_id: str | None = None
    document_id: str | None = None
    approval_ids: list[str] = field(default_factory=list)
    comment_ids: list[str] = field(default_factory=list)
    traces: list[ApiTrace] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BugReport:
    """Structured failure report emitted by the bug logger agent."""

    id: str
    run_id: str
    title: str
    severity: BugSeverity
    expected: str
    actual: str
    repro_steps: tuple[str, ...]
    api_traces: tuple[ApiTrace, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    screenshot_paths: tuple[str, ...] = ()
    log_excerpt: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("bug report title must not be blank")
        if not self.repro_steps:
            raise ValueError("bug report requires at least one repro step")


@dataclass
class ScenarioResult:
    """Outcome of one scenario run."""

    name: str
    state: ScenarioState
    bug_reports: list[BugReport] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.bug_reports
