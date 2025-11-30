"""Public vs internal status helpers."""

from __future__ import annotations

from typing import Dict

from . import documents as documents_module
from . import logs as logs_module
from . import search as search_module
from . import workflows as workflows_module


def _safe_len(obj: object) -> int:
    """Return ``len(obj)`` but gracefully handle non-sized objects."""
    try:
        return len(obj)  # type: ignore[arg-type]
    except Exception:
        return 0


def public_status() -> Dict[str, int]:
    """Return counts safe for public display."""
    # Importing the modules above instead of the underlying data structures
    # ensures we always reflect the latest global state. Other modules may
    # replace ``documents`` or ``projects`` with new objects during tests, so
    # we resolve them dynamically at call time rather than capturing stale
    # references at import time.
    return {
        "projects": _safe_len(getattr(search_module, "projects", [])),
        "documents": _safe_len(getattr(documents_module, "documents", [])),
    }


def internal_status() -> Dict[str, int]:
    """Return extended status including internal metrics."""
    data = public_status()
    data.update(
        {
            "workflows": _safe_len(getattr(workflows_module, "workflows", [])),
            "logs": (logs_module.count_logs() if hasattr(logs_module, "count_logs") else 0),
        }
    )
    return data
