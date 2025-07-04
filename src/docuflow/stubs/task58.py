"""Records Keeper archival folder helper."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..records_keeper import create_archival_folder
from . import record_task_completion


def task58(project_id: str | None = None, base: str | Path | None = None) -> None:
    """Create an archival folder for ``project_id`` under ``base``."""
    project = project_id or "general"
    target_base = Path(base) if base else Path(tempfile.gettempdir()) / "records"
    create_archival_folder(target_base, project)
    record_task_completion(58)
    return None
