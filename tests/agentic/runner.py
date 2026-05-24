from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from agentic.models import ScenarioResult

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DIR = Path(
    os.environ.get(
        "DOCREVIEW360_AGENTIC_STATE_DIR",
        str(REPO_ROOT / "tests" / "agentic" / ".state"),
    )
)


def _configure_local_environment() -> None:
    DEFAULT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DOCREVIEW360_SECRET_KEY", "agentic-test-secret")
    os.environ.setdefault("DOCREVIEW360_ALGORITHM", "HS256")
    os.environ.setdefault("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "30")
    os.environ.setdefault("DOCREVIEW360_REFRESH_EXPIRE_DAYS", "30")
    os.environ.setdefault("DOCREVIEW360_TOKEN_ISSUER", "agentic-issuer")
    os.environ.setdefault("DOCREVIEW360_TOKEN_AUDIENCE", "agentic-audience")
    os.environ.setdefault("DOCREVIEW360_OIDC_SECRET_KEY", "agentic-oidc-secret")
    os.environ.setdefault("DOCREVIEW360_OIDC_ALGORITHM", "HS256")
    os.environ.setdefault("DOCREVIEW360_OIDC_EXPIRE_MINUTES", "30")
    os.environ.setdefault("DOCREVIEW360_OIDC_TOKEN_ISSUER", "agentic-oidc-issuer")
    os.environ.setdefault("DOCREVIEW360_OIDC_TOKEN_AUDIENCE", "agentic-oidc-audience")
    os.environ.setdefault("DOCREVIEW360_REQUIRE_MFA", "0")
    os.environ.setdefault("DOCREVIEW360_SEED_DEMO_USERS", "0")
    os.environ.setdefault("DOCREVIEW360_MAX_FAILED_ATTEMPTS", "5")
    os.environ.setdefault("DOCREVIEW360_LOCKOUT_SECONDS", "300")
    os.environ.setdefault("DOCREVIEW360_ENV", "dev")
    os.environ.setdefault("DOCREVIEW360_USER_DB", str(DEFAULT_STATE_DIR / "users.db"))
    os.environ.setdefault("DOCREVIEW360_RBAC_DB", str(DEFAULT_STATE_DIR / "roles.db"))
    os.environ.setdefault("DOCREVIEW360_SEARCH_DB", str(DEFAULT_STATE_DIR / "search.db"))


if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    sys.path.insert(0, str(REPO_ROOT / "tests"))

_configure_local_environment()

_NOISY_LOGGERS: list[tuple[str, int]] = [
    ("httpx", logging.WARNING),
    ("docreview360.cache", logging.ERROR),
    ("docreview360.approvals.core", logging.ERROR),
    ("docreview360.search._indexing", logging.ERROR),
]


def run_agentic_suite(
    *,
    run_id: str | None = None,
    bug_report_dir: Path | None = None,
    max_steps: int = 100,
) -> list[ScenarioResult]:
    """Run the first guarded agentic scenario suite."""

    from fastapi.testclient import TestClient

    from agentic.agents import OrchestratorAgent
    from agentic.models import AgenticRunConfig
    from agentic.scenarios import run_document_review_scenario
    from docreview360.api import app

    saved_levels = [(name, logging.getLogger(name).level) for name, _ in _NOISY_LOGGERS]
    for name, level in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(level)
    try:
        resolved_run_id = run_id or uuid4().hex[:10]
        config = AgenticRunConfig(
            run_id=resolved_run_id,
            bug_report_dir=bug_report_dir or Path(__file__).parent / "bug-reports",
            max_steps=max_steps,
        )
        orchestrator = OrchestratorAgent(client=TestClient(app), config=config)
        return [
            orchestrator.run(
                name="document-review-workflow",
                scenario=run_document_review_scenario,
            )
        ]
    finally:
        for name, level in saved_levels:
            logging.getLogger(name).setLevel(level)


def run_browser_suite(
    *,
    run_id: str | None,
    bug_report_dir: Path | None,
    frontend_url: str,
    backend_url: str,
    headed: bool,
    slow_mo_ms: int,
) -> list[ScenarioResult]:
    from agentic.browser_agent import run_browser_ckeditor_suite
    from agentic.models import BrowserRunConfig

    resolved_run_id = run_id or uuid4().hex[:10]
    config = BrowserRunConfig(
        frontend_url=frontend_url,
        backend_url=backend_url,
        headed=headed,
        slow_mo_ms=slow_mo_ms,
    )
    return run_browser_ckeditor_suite(
        run_id=resolved_run_id,
        config=config,
        bug_report_dir=bug_report_dir or Path(__file__).parent / "bug-reports",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DocReview360 agentic QA scenarios.")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--bug-report-dir", type=Path, default=None)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Run the watchable browser layer instead of the API-only layer.",
    )
    parser.add_argument("--frontend-url", default=os.getenv("E2E_FRONTEND_URL"))
    parser.add_argument("--backend-url", default=os.getenv("E2E_BACKEND_URL"))
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser mode without a visible headed browser.",
    )
    parser.add_argument("--slowmo-ms", type=int, default=400)
    args = parser.parse_args()

    if args.ui:
        if not args.frontend_url or not args.backend_url:
            parser.error("--ui requires --frontend-url and --backend-url, or E2E_* env vars")
        results = run_browser_suite(
            run_id=args.run_id,
            bug_report_dir=args.bug_report_dir,
            frontend_url=args.frontend_url,
            backend_url=args.backend_url,
            headed=not args.headless,
            slow_mo_ms=args.slowmo_ms,
        )
    else:
        results = run_agentic_suite(
            run_id=args.run_id,
            bug_report_dir=args.bug_report_dir,
            max_steps=args.max_steps,
        )
    failed = [result for result in results if not result.passed]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name} ({len(result.state.traces)} API steps)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
