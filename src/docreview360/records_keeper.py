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
        # ``" "`` on disk.  Normalise by rejecting such values early.
        raise ValueError("project_id must be provided")
    base_path = Path(base)
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    folder = base_path / project_id / date_part
    folder.mkdir(parents=True, exist_ok=True)
    return folder
