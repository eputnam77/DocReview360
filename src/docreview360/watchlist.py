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
        if not isinstance(data, dict):
            raise ValueError(f"Watchlist file must contain a JSON object: {WATCHLIST_FILE}")
        return {u: set(v) for u, v in data.items()}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        # Previously a malformed watchlist file resulted in an empty
        # dictionary being returned which silently discarded all saved
        # watchers.  Propagate the issue so callers are aware that the
        # persistence layer is corrupt instead of quietly losing data.
        raise ValueError(f"Invalid JSON in watchlist file: {WATCHLIST_FILE}") from exc


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
    user = user.strip()
    project_id = project_id.strip()
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
    user = user.strip()
    if not user:
        raise ValueError("user required")
    return sorted(_watchlist.get(user, set()))


def get_watchers(project_id: str) -> List[str]:
    """Return users watching the given project."""
    pid = project_id.strip()
    if not pid:
        raise ValueError("project_id required")
    return sorted(u for u, projects in _watchlist.items() if pid in projects)
