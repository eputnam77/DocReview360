"""Simplistic HR API sync utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping

from .search import assign_temporary


def sync_temp_reassignments(records: Iterable[Mapping[str, str]]) -> int:
    """Synchronise temporary assignments from HR data.

    Each ``record`` should contain ``project``, ``user`` and ``until`` (ISO date)
    keys. Invalid entries are skipped.

    Returns
    -------
    int
        Number of successfully processed records.
    """
    count = 0
    for record in records:
        try:
            project = record["project"]
            user = record["user"]
            until = datetime.fromisoformat(record["until"])
        except (KeyError, ValueError):
            # ignore malformed rows
            continue
        if until <= datetime.now(timezone.utc):
            # skip expired assignments
            continue
        assign_temporary(project, user, until, approved=True)
        count += 1
    return count
