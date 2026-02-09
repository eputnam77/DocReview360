"""Helpers for configuring the app in end-to-end (E2E) mode."""

from __future__ import annotations

import os
from pathlib import Path

_RUNTIME_DIR_ENV = "E2E_RUN_DIR"


def _normalize_run_dir(raw: str | None) -> Path | None:
    if raw is None:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    return Path(candidate).expanduser().resolve()


def get_e2e_run_dir() -> Path | None:
    """Return the configured E2E run directory, if any."""

    return _normalize_run_dir(os.getenv(_RUNTIME_DIR_ENV))


def apply_e2e_run_dir() -> Path | None:
    """Apply E2E runtime paths derived from ``E2E_RUN_DIR``.

    Returns the resolved run directory when configured, otherwise ``None``.
    """

    run_dir = get_e2e_run_dir()
    if run_dir is None:
        return None

    db_dir = run_dir / "db"
    uploads_dir = run_dir / "uploads"
    logs_dir = run_dir / "logs"
    tmp_dir = run_dir / "tmp"
    artifacts_dir = run_dir / "artifacts"

    for path in (db_dir, uploads_dir, logs_dir, tmp_dir, artifacts_dir):
        path.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault(
        "DOCREVIEW360_DATABASE_URL", f"sqlite:///{(db_dir / 'docreview360.db').as_posix()}"
    )
    os.environ.setdefault("DOCREVIEW360_USER_DB", str(db_dir / "docreview360_users.db"))
    os.environ.setdefault("DOCREVIEW360_RBAC_DB", str(db_dir / "docreview360_roles.db"))
    os.environ.setdefault("DOCREVIEW360_SEARCH_DB", str(db_dir / "search_state.db"))
    os.environ.setdefault("DOCREVIEW360_DOC_TYPES_FILE", str(run_dir / "document_types.json"))
    os.environ.setdefault("DOCREVIEW360_PHASES_FILE", str(run_dir / "phases.json"))
    os.environ.setdefault(
        "DOCREVIEW360_WORKFLOW_TEMPLATES_FILE",
        str(run_dir / "workflow_templates.json"),
    )
    os.environ.setdefault("DOCREVIEW360_TEMPLATE_STORE_FILE", str(run_dir / "template_store.json"))
    os.environ.setdefault("DOCREVIEW360_TEMPLATES_DIR", str(run_dir / "templates"))
    os.environ.setdefault("DOCREVIEW360_SETTINGS_FILE", str(run_dir / "settings.yaml"))
    os.environ.setdefault("DOCREVIEW360_CONFIG_FILE", str(run_dir / "docreview360.yaml"))
    os.environ.setdefault("DOCREVIEW360_ENVIRONMENTS_FILE", str(run_dir / "environments.yaml"))
    os.environ.setdefault("DOCREVIEW360_WORKER_STATE", str(run_dir / "worker_state.json"))
    os.environ.setdefault("DOCREVIEW360_ARCHIVE_BUCKET", str(run_dir / "archive_store"))
    os.environ.setdefault("DOCREVIEW360_SAMPLE_DIR", str(run_dir / "samples"))

    for temp_var in ("TMPDIR", "TEMP", "TMP"):
        os.environ.setdefault(temp_var, str(tmp_dir))

    return run_dir
