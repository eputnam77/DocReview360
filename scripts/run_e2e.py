#!/usr/bin/env python3
"""Run the DocReview360 E2E suite in a sandbox-friendly way."""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import IO
from urllib.request import Request, urlopen


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for(url: str, timeout_s: float = 45.0) -> None:
    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    while time.time() < deadline:
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


def main() -> int:
    run_id = os.getenv("E2E_RUN_ID") or _now_run_id()
    run_root = Path(".e2e-runs") / run_id
    db_dir = run_root / "db"
    uploads_dir = run_root / "uploads"
    logs_dir = run_root / "logs"
    tmp_dir = run_root / "tmp"
    artifacts_dir = run_root / "artifacts"
    for path in (db_dir, uploads_dir, logs_dir, tmp_dir, artifacts_dir):
        path.mkdir(parents=True, exist_ok=True)

    backend_port = int(os.getenv("E2E_BACKEND_PORT") or _find_free_port())
    frontend_port = int(os.getenv("E2E_FRONTEND_PORT") or _find_free_port())

    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    env = os.environ.copy()
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
            "TMPDIR": str(tmp_dir),
            "TEMP": str(tmp_dir),
            "TMP": str(tmp_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "NEXT_PUBLIC_API_BASE": backend_url,
            "NEXT_DIST_DIR": str(run_root / "next"),
            "NEXT_TELEMETRY_DISABLED": "1",
            "E2E_BACKEND_URL": backend_url,
            "E2E_FRONTEND_URL": frontend_url,
        }
    )

    backend_log = _open_log(logs_dir / "backend.log")
    frontend_log = _open_log(logs_dir / "frontend.log")

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

    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", str(frontend_port)],
        cwd="frontend",
        env=env,
        stdout=frontend_log,
        stderr=frontend_log,
        text=True,
    )

    try:
        _wait_for(f"{backend_url}/health")
        _wait_for(f"{frontend_url}/api/ping")
        _post_json(f"{backend_url}/e2e/seed")

        pytest_cmd = [
            "pytest",
            "-m",
            "e2e",
            "-p",
            "no:cacheprovider",
            "--output",
            str(artifacts_dir),
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
