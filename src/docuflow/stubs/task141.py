"""Implementation for task 141."""

from pathlib import Path

from ..setup_wizard import run_setup
from . import record_task_completion


def task141(path: Path | None = None) -> None:
    """Run the first-run setup wizard with sample values."""

    run_setup(
        database="sqlite:///docuflow.db",
        keycloak_url="https://keycloak.local",
        editor="tiptap",
        storage="minio",
        bucket="docs",
        path=path,
    )
    record_task_completion(141)
    return None
