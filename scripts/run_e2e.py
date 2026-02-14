#!/usr/bin/env python3
"""Run the DocReview360 E2E suite in a sandbox-friendly way."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import IO
from urllib.request import Request, urlopen


def _now_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for(
    url: str,
    timeout_s: float = 120.0,
    proc: subprocess.Popen[str] | None = None,
    proc_name: str = "service",
) -> None:
    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(
                f"{proc_name} exited with code {proc.returncode} while waiting for {url}"
            )
        try:
            with urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 300:
                    return
        except Exception as exc:  # noqa: BLE001 - surface after timeout
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}") from last_error


def _post_json(url: str) -> dict:
    req = Request(url, method="POST")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _open_log(path: Path) -> IO[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("w", encoding="utf-8")


def _terminate(proc: subprocess.Popen[str], name: str) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
        print(f"[e2e] Force killed {name}", file=sys.stderr)


def _resolve_npm_executable() -> str:
    npm_cmd = shutil.which("npm.cmd")
    if npm_cmd:
        return npm_cmd
    npm_bin = shutil.which("npm")
    if npm_bin:
        return npm_bin
    raise RuntimeError("npm executable not found in PATH")


def _resolve_next_executable(frontend_workspace: Path) -> str:
    next_bin_name = "next.cmd" if os.name == "nt" else "next"
    next_bin = frontend_workspace / "node_modules" / ".bin" / next_bin_name
    if next_bin.exists():
        return str(next_bin.resolve())
    raise RuntimeError("Next.js executable not found in frontend/node_modules/.bin")


def _resolve_node_executable() -> str:
    node_bin = shutil.which("node")
    if node_bin:
        return node_bin
    raise RuntimeError("node executable not found in PATH")


def _next_cli_script(frontend_workspace: Path) -> str:
    script = frontend_workspace / "node_modules" / "next" / "dist" / "bin" / "next"
    if script.exists():
        return str(script.resolve())
    raise RuntimeError("Next.js CLI script not found in frontend/node_modules/next")


def _start_frontend(
    *,
    frontend_workspace: Path,
    frontend_mode: str,
    frontend_port: int,
    node_executable: str,
    next_cli: str,
    env: dict[str, str],
    frontend_log: IO[str],
) -> tuple[subprocess.Popen[str], dict[str, str]]:
    frontend_env = env.copy()
    if frontend_mode == "start":
        frontend_env.pop("NEXT_DIST_DIR", None)
        frontend_cmd = [
            node_executable,
            next_cli,
            "start",
            "-H",
            "0.0.0.0",
            "-p",
            str(frontend_port),
        ]
    else:
        frontend_dev_engine = _select_frontend_dev_engine()
        frontend_cmd = [
            node_executable,
            next_cli,
            "dev",
            *(["--webpack"] if frontend_dev_engine == "webpack" else []),
            "-H",
            "0.0.0.0",
            "-p",
            str(frontend_port),
        ]
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_workspace,
        env=frontend_env,
        stdout=frontend_log,
        stderr=frontend_log,
        text=True,
    )
    return frontend_proc, frontend_env


def _ensure_frontend_build(
    *,
    frontend_workspace: Path,
    node_executable: str,
    next_cli: str,
    env: dict[str, str],
    frontend_log: IO[str],
) -> None:
    build_id = frontend_workspace / ".next" / "BUILD_ID"
    if build_id.exists():
        return
    build_env = env.copy()
    build_env.pop("NEXT_DIST_DIR", None)
    subprocess.check_call(
        [node_executable, next_cli, "build"],
        cwd=frontend_workspace,
        env=build_env,
        stdout=frontend_log,
        stderr=frontend_log,
        text=True,
    )


def _select_frontend_mode(frontend_workspace: Path) -> str:
    requested = (os.getenv("E2E_FRONTEND_MODE") or "").strip().lower()
    if requested in {"dev", "start"}:
        return requested
    # Default to dev mode for correctness: `next start` serves a prebuilt bundle
    # where NEXT_PUBLIC_* values may be stale and cause E2E drift.
    return "dev"


def _select_frontend_dev_engine() -> str:
    requested = (os.getenv("E2E_FRONTEND_DEV_ENGINE") or "").strip().lower()
    if requested in {"webpack", "turbopack"}:
        return requested
    # Prefer webpack for E2E stability. Turbopack currently returns intermittent
    # route-level 500s in this codebase under Playwright load.
    return "webpack"


def _select_e2e_mark_expression() -> str:
    requested = (os.getenv("E2E_TEST_MARK") or "").strip()
    if requested:
        return requested
    return "e2e"


def _select_playwright_artifact_mode() -> tuple[str, str, str]:
    requested = (os.getenv("E2E_PLAYWRIGHT_ARTIFACTS") or "").strip().lower()
    if not requested:
        requested = "failure"
    if requested in {"off", "none"}:
        return "off", "off", "off"
    if requested in {"failure", "on-failure", "only-on-failure"}:
        return "only-on-failure", "retain-on-failure", "retain-on-failure"
    if requested in {"on", "always", "all"}:
        return "on", "on", "on"
    raise RuntimeError(
        "Unsupported E2E_PLAYWRIGHT_ARTIFACTS value. "
        "Use one of: off, failure, on."
    )


def _ensure_frontend_workspace(
    source_dir: Path, workspace_dir: Path, env: dict, npm_executable: str
) -> Path:
    source_next_bin = source_dir / "node_modules" / ".bin" / "next"
    if source_next_bin.exists():
        # Prefer reusing the local frontend workspace when dependencies are already
        # installed. This keeps E2E runs offline-friendly.
        return source_dir

    frontend_workspace = workspace_dir / "frontend"
    if not frontend_workspace.exists():
        # Keep the E2E copy lean and deterministic: runtime outputs and installed
        # dependencies are recreated per run and can fail to copy on Windows.
        shutil.copytree(
            source_dir,
            frontend_workspace,
            ignore=shutil.ignore_patterns(".next", "node_modules"),
        )

    next_bin = frontend_workspace / "node_modules" / ".bin" / "next"
    if not next_bin.exists():
        npm_env = env.copy()
        subprocess.check_call(
            [npm_executable, "install", "--no-save", "--no-package-lock"],
            cwd=frontend_workspace,
            env=npm_env,
        )
    return frontend_workspace


def _configure_git_https(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            "git",
            "config",
            "--file",
            str(config_path),
            "url.https://github.com/.insteadOf",
            "ssh://git@github.com/",
        ]
    )


def main() -> int:
    run_id = os.getenv("E2E_RUN_ID") or _now_run_id()
    run_root = Path(os.getenv("E2E_RUN_DIR") or (Path(".e2e-runs") / run_id))
    db_dir = run_root / "db"
    uploads_dir = run_root / "uploads"
    logs_dir = run_root / "logs"
    tmp_dir = run_root / "tmp"
    artifacts_dir = run_root / "artifacts"
    workspace_dir = run_root / "workspace"
    for path in (db_dir, uploads_dir, logs_dir, tmp_dir, artifacts_dir, workspace_dir):
        path.mkdir(parents=True, exist_ok=True)

    git_config = tmp_dir / "gitconfig"
    _configure_git_https(git_config)

    backend_port = int(os.getenv("E2E_BACKEND_PORT") or _find_free_port())
    frontend_port = int(os.getenv("E2E_FRONTEND_PORT") or _find_free_port())

    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    startup_timeout_s = float(os.getenv("E2E_STARTUP_TIMEOUT_S") or "120")
    e2e_mark_expression = _select_e2e_mark_expression()

    env = os.environ.copy()
    pythonpath_parts = [str(Path("src").resolve())]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env.update(
        {
            "E2E_RUN_DIR": str(run_root),
            "DOCREVIEW360_E2E_MODE": "1",
            "DOCREVIEW360_ENV": "test",
            "DOCREVIEW360_DATABASE_URL": f"sqlite:///{(db_dir / 'docreview360.db').as_posix()}",
            "DOCREVIEW360_USER_DB": str(db_dir / "docreview360_users.db"),
            "DOCREVIEW360_RBAC_DB": str(db_dir / "docreview360_roles.db"),
            "DOCREVIEW360_SEARCH_DB": str(db_dir / "search_state.db"),
            "DOCREVIEW360_DOC_TYPES_FILE": str(run_root / "document_types.json"),
            "DOCREVIEW360_PHASES_FILE": str(run_root / "phases.json"),
            "DOCREVIEW360_WORKFLOW_TEMPLATES_FILE": str(run_root / "workflow_templates.json"),
            "DOCREVIEW360_TEMPLATE_STORE_FILE": str(run_root / "template_store.json"),
            "DOCREVIEW360_TEMPLATES_DIR": str(run_root / "templates"),
            "DOCREVIEW360_SETTINGS_FILE": str(run_root / "settings.yaml"),
            "DOCREVIEW360_CONFIG_FILE": str(run_root / "docreview360.yaml"),
            "DOCREVIEW360_ENVIRONMENTS_FILE": str(run_root / "environments.yaml"),
            "DOCREVIEW360_WORKER_STATE": str(run_root / "worker_state.json"),
            "DOCREVIEW360_ARCHIVE_BUCKET": str(run_root / "archive_store"),
            "DOCREVIEW360_SAMPLE_DIR": str(run_root / "samples"),
            "DOCREVIEW360_DATA_DIR": str(workspace_dir),
            "TMPDIR": str(tmp_dir),
            "TEMP": str(tmp_dir),
            "TMP": str(tmp_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "NEXT_PUBLIC_API_BASE": backend_url,
            "NEXT_DIST_DIR": str(run_root / "next"),
            "NEXT_TELEMETRY_DISABLED": "1",
            "E2E_BACKEND_URL": backend_url,
            "E2E_FRONTEND_URL": frontend_url,
            # Browser-side API calls originate from the frontend dev server's
            # ephemeral port; allow that origin so authenticated writes (POST/PUT)
            # are not blocked by CORS preflight during E2E.
            "DOCREVIEW360_ALLOW_ORIGINS": ",".join(
                [
                    frontend_url,
                    f"http://127.0.0.1:{frontend_port}",
                    f"http://localhost:{frontend_port}",
                ]
            ),
            "PYTHONPATH": os.pathsep.join(pythonpath_parts),
            "NPM_CONFIG_CACHE": str((tmp_dir / "npm-cache").resolve()),
            "GIT_CONFIG_GLOBAL": str(git_config.resolve()),
            "GIT_CONFIG_NOSYSTEM": "1",
        }
    )

    backend_log = _open_log(logs_dir / "backend.log")
    frontend_log = _open_log(logs_dir / "frontend.log")
    npm_executable = _resolve_npm_executable()

    backend_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "docreview360.api:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(backend_port),
            "--log-level",
            "info",
        ],
        env=env,
        stdout=backend_log,
        stderr=backend_log,
        text=True,
    )

    frontend_workspace = _ensure_frontend_workspace(
        Path("frontend"), workspace_dir, env, npm_executable
    )
    frontend_mode = _select_frontend_mode(frontend_workspace)
    _resolve_next_executable(frontend_workspace)
    node_executable = _resolve_node_executable()
    next_cli = _next_cli_script(frontend_workspace)
    if frontend_mode == "start":
        _ensure_frontend_build(
            frontend_workspace=frontend_workspace,
            node_executable=node_executable,
            next_cli=next_cli,
            env=env,
            frontend_log=frontend_log,
        )
    frontend_proc, _ = _start_frontend(
        frontend_workspace=frontend_workspace,
        frontend_mode=frontend_mode,
        frontend_port=frontend_port,
        node_executable=node_executable,
        next_cli=next_cli,
        env=env,
        frontend_log=frontend_log,
    )

    try:
        _wait_for(
            f"{backend_url}/health",
            timeout_s=startup_timeout_s,
            proc=backend_proc,
            proc_name="backend",
        )
        try:
            _wait_for(
                f"{frontend_url}/api/ping",
                timeout_s=startup_timeout_s,
                proc=frontend_proc,
                proc_name="frontend",
            )
        except RuntimeError as exc:
            can_fallback = frontend_mode == "dev" and frontend_proc.poll() is not None
            if not can_fallback:
                raise
            print(
                f"[e2e] Frontend dev startup failed ({exc}); falling back to next start",
                file=sys.stderr,
            )
            _terminate(frontend_proc, "frontend")
            _ensure_frontend_build(
                frontend_workspace=frontend_workspace,
                node_executable=node_executable,
                next_cli=next_cli,
                env=env,
                frontend_log=frontend_log,
            )
            frontend_proc, _ = _start_frontend(
                frontend_workspace=frontend_workspace,
                frontend_mode="start",
                frontend_port=frontend_port,
                node_executable=node_executable,
                next_cli=next_cli,
                env=env,
                frontend_log=frontend_log,
            )
            _wait_for(
                f"{frontend_url}/api/ping",
                timeout_s=startup_timeout_s,
                proc=frontend_proc,
                proc_name="frontend",
            )
        _post_json(f"{backend_url}/e2e/seed")

        playwright_options: list[str] = []
        try:
            import pytest_playwright  # noqa: F401
        except Exception:
            playwright_options = []
        else:
            screenshot_mode, video_mode, tracing_mode = _select_playwright_artifact_mode()
            playwright_options = [
                f"--screenshot={screenshot_mode}",
                f"--video={video_mode}",
                f"--tracing={tracing_mode}",
                "--output",
                str(artifacts_dir),
            ]

        pytest_cmd = [
            "pytest",
            "tests/e2e",
            "-m",
            e2e_mark_expression,
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            *playwright_options,
        ]
        result = subprocess.call(pytest_cmd, env=env)
    finally:
        _terminate(backend_proc, "backend")
        _terminate(frontend_proc, "frontend")
        backend_log.close()
        frontend_log.close()

    keep = env.get("KEEP_E2E_ARTIFACTS") == "1"
    if result == 0 and not keep:
        shutil.rmtree(run_root, ignore_errors=True)
    else:
        print(f"[e2e] Run artifacts kept at {run_root}", file=sys.stderr)

    return result


if __name__ == "__main__":
    sys.exit(main())
