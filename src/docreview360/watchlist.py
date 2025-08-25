"""Project Watchlist utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Set

WATCHLIST_FILE = Path(
    os.environ.get("DOCREV_WATCHLIST_FILE", str(Path(__file__).with_name("watchlist.json")))
)


def _load() -> Dict[str, Set[str]]:
    try:
        data = json.loads(WATCHLIST_FILE.read_text())
        return {u: set(v) for u, v in data.items()}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save(watchlist: Dict[str, Set[str]]) -> None:
    serializable = {u: sorted(list(v)) for u, v in watchlist.items()}
    # Ensure the directory exists when a custom ``DOCREV_WATCHLIST_FILE`` points
    # to a non-existent folder.  Without this ``write_text`` would raise a
    # ``FileNotFoundError`` and the caller would lose watchlist updates.
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_FILE.write_text(json.dumps(serializable, indent=2))


_watchlist: Dict[str, Set[str]] = _load()


def toggle_watch(user: str, project_id: str) -> List[str]:
    """Toggle ``project_id`` in ``user``'s watchlist and return updated list."""
    if not user or not project_id:
        raise ValueError("user and project_id required")
    starred = _watchlist.setdefault(user, set())
    if project_id in starred:
        starred.remove(project_id)
    else:
        starred.add(project_id)
    _save(_watchlist)
    return sorted(starred)


def get_watchlist(user: str) -> List[str]:
    """Return the sorted watchlist for ``user``."""
    return sorted(_watchlist.get(user, set()))


def get_watchers(project_id: str) -> List[str]:
    """Return users watching the given project."""
    return sorted(u for u, projects in _watchlist.items() if project_id in projects)
