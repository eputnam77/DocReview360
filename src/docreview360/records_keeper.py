"""Helpers for Records Keeper archival folder structure."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def create_archival_folder(base: str | Path, project_id: str) -> Path:
    """Create and return an archival folder for ``project_id``.

    The folder name embeds today's UTC date to keep daily snapshots
    grouped by project.
    """
    if not project_id or not project_id.strip():
        # ``project_id`` is used as part of the path.  An empty string or one
        # that contains only whitespace would create confusing folders like
        # ``" "`` on disk.  Normalize by rejecting such values early.
        raise ValueError("project_id must be provided")
    # Prevent path traversal.  ``Path(project_id)`` normalizes separators but
    # still yields multiple parts for values like ``"../etc"`` or ``"a/b"``.
    # Restrict project identifiers to a single path segment without special
    # values so archived files cannot escape the configured base directory.
    pid_path = Path(project_id)
    if pid_path.is_absolute() or len(pid_path.parts) != 1 or pid_path.parts[0] in {"..", "."}:
        raise ValueError("project_id must be a simple name")
    base_path = Path(base)
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    folder = base_path / pid_path.name / date_part
    folder.mkdir(parents=True, exist_ok=True)
    return folder
