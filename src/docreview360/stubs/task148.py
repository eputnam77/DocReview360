"""Implementation for task 148."""

from pathlib import Path

from ..rbac_editor import update_permission


def task148(path: Path | None = None) -> None:
    """Modify RBAC permissions."""

    update_permission("pm", "delete_project", False, path=path or Path("rbac.yaml"))
