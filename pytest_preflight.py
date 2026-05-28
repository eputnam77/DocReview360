"""Pytest runner environment validation for DocReview360."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

SUPPORTED_PYTHON = ">=3.11,<3.13"
REQUIRED_TEST_IMPORTS = {
    "celery": "celery",
    "fastapi": "fastapi",
    "jose": "python-jose[cryptography]",
    "prometheus_client": "prometheus-client",
    "sqlalchemy": "SQLAlchemy",
}


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _exit_invalid(message: str) -> None:
    pytest.exit(f"DOCREVIEW360_TEST_ENV_INVALID: {message}", returncode=2)


def validate_test_environment() -> None:
    """Fail fast when the local Python runner cannot run the test suite."""

    if sys.version_info < (3, 11) or sys.version_info >= (3, 13):
        _exit_invalid(
            "Python test runner must use "
            f"{SUPPORTED_PYTHON}; found {sys.version.split()[0]}. "
            "Create a Python 3.11 or 3.12 environment and install the project "
            "with test dependencies before running pytest."
        )

    missing = [
        requirement
        for module_name, requirement in REQUIRED_TEST_IMPORTS.items()
        if importlib.util.find_spec(module_name) is None
    ]
    if missing:
        _exit_invalid(
            "Missing required test dependencies: "
            f"{', '.join(sorted(missing))}. Install the project with test "
            "dependencies before running pytest."
        )


def configure_test_tempdir(base_dir: Path) -> None:
    """Ensure pytest temp directories are writable for this workspace."""

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            probe_file = Path(temp_dir) / "probe.txt"
            probe_file.write_text("ok", encoding="utf-8")
        return
    except Exception as error:
        default_error = _format_error(error)
        fallback = base_dir / ".tmp" / f"pytest-{uuid4().hex}"

    try:
        fallback.mkdir(parents=True, exist_ok=True)
        probe_file = fallback / "probe.txt"
        probe_file.write_text("ok", encoding="utf-8")
    except Exception as fallback_error:
        _exit_invalid(
            "Python test runner cannot create a writable temporary directory. "
            f"Default temp failed with {default_error}; "
            f"fallback {fallback} failed with {_format_error(fallback_error)}. "
            "Set TMP, TEMP, or TMPDIR to a writable directory before running pytest."
        )

    os.environ["TMPDIR"] = str(fallback)
    os.environ["TEMP"] = str(fallback)
    os.environ["TMP"] = str(fallback)
    tempfile.tempdir = str(fallback)
