# SPDX-License-Identifier: MIT
"""Dashboard widget visibility helpers — SQLite-backed (Item 45 Phase 3).

Preferences are stored in the ``dashboard_visibility`` table via
:class:`~docreview360.models.DashboardVisibilityRecord`.  If the database
is unavailable the module falls back to ``settings_manager`` so that existing
deployments are not broken during the migration window.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

_logger = logging.getLogger(__name__)

DEFAULT_VISIBILITY: Dict[str, bool] = {
    "stats": True,
    "status": True,
    "activity": True,
    "logs": True,
}


def _get_db():  # type: ignore[return]
    """Return the shared :class:`~docreview360.database.Database` instance.

    Imports lazily to avoid circular imports at module load time.
    Uses the same singleton that the rest of the application relies on.
    """
    from .logs._db import _get_db as _logs_get_db  # noqa: PLC0415

    return _logs_get_db()


def get_visibility(user: str) -> Dict[str, Any]:
    """Return widget visibility settings for *user*.

    The returned dict always contains the four legacy boolean keys from
    ``DEFAULT_VISIBILITY`` merged with whatever the user last saved.  It
    also includes a ``widgets`` key holding the list of widget IDs that the
    user has selected (empty list means "use defaults").
    """
    try:
        db = _get_db()
        with db.orm_session() as session:
            from .models import DashboardVisibilityRecord  # noqa: PLC0415

            record = session.get(DashboardVisibilityRecord, user)
            if record is None:
                return {**DEFAULT_VISIBILITY, "widgets": []}
            stored: Dict[str, Any] = dict(record.widgets) if record.widgets else {}
            result = {**DEFAULT_VISIBILITY}
            # Merge legacy bool keys (stats/status/activity/logs)
            for key in DEFAULT_VISIBILITY:
                if key in stored:
                    result[key] = bool(stored[key])
            result["widgets"] = stored.get("widgets", [])
            return result
    except Exception as exc:  # pragma: no cover — DB unavailable fallback
        _logger.warning("dashboard_prefs: DB unavailable, falling back to settings_manager: %s", exc)
        try:
            from .settings_manager import load_settings  # noqa: PLC0415

            data = load_settings()
            stored = data.get(f"dash_{user}", {})
            return {**DEFAULT_VISIBILITY, **stored, "widgets": stored.get("widgets", [])}
        except Exception:
            return {**DEFAULT_VISIBILITY, "widgets": []}


def set_visibility(user: str, visibility: Dict[str, Any]) -> Dict[str, Any]:
    """Persist visibility settings for *user* and return the merged result.

    *visibility* may contain any combination of:
    - Legacy boolean keys (``stats``, ``status``, ``activity``, ``logs``).
    - A ``widgets`` key holding a list of visible widget IDs.
    """
    try:
        db = _get_db()
        with db.orm_session() as session:
            from .models import DashboardVisibilityRecord  # noqa: PLC0415

            record = session.get(DashboardVisibilityRecord, user)
            existing: Dict[str, Any] = dict(record.widgets) if (record and record.widgets) else {}

            # Merge incoming values
            for key, value in visibility.items():
                if key == "widgets":
                    existing["widgets"] = list(value) if isinstance(value, list) else []
                else:
                    existing[key] = bool(value)

            if record is None:
                record = DashboardVisibilityRecord(username=user, widgets=existing)
                session.add(record)
            else:
                record.widgets = existing

            # Build return value
            result: Dict[str, Any] = {**DEFAULT_VISIBILITY}
            for key in DEFAULT_VISIBILITY:
                if key in existing:
                    result[key] = bool(existing[key])
            result["widgets"] = existing.get("widgets", [])
            return result
    except Exception as exc:  # pragma: no cover — DB unavailable fallback
        _logger.warning("dashboard_prefs: DB unavailable, falling back to settings_manager: %s", exc)
        try:
            from .settings_manager import load_settings, update_setting  # noqa: PLC0415

            data = load_settings()
            current: Dict[str, Any] = {**DEFAULT_VISIBILITY, **data.get(f"dash_{user}", {})}
            for key, value in visibility.items():
                if key == "widgets":
                    current["widgets"] = list(value) if isinstance(value, list) else []
                else:
                    current[key] = bool(value)
            update_setting(f"dash_{user}", current)
            return current
        except Exception:
            return {**DEFAULT_VISIBILITY, "widgets": []}
