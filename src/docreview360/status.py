"""Public vs internal status helpers."""

from __future__ import annotations

from typing import Dict

from . import documents as documents_module
from . import logs as logs_module
from . import search as search_module
from . import workflows as workflows_module


def public_status() -> Dict[str, int]:
    """Return counts safe for public display."""
    # Importing the modules above instead of the underlying data structures
    # ensures we always reflect the latest global state. Other modules may
    # replace ``documents`` or ``projects`` with new objects during tests, so
    # we resolve them dynamically at call time rather than capturing stale
    # references at import time.
    return {
        "projects": len(search_module.projects),
        "documents": len(documents_module.documents),
    }


def internal_status() -> Dict[str, int]:
    """Return extended status including internal metrics."""
    data = public_status()
    data.update(
        {
            "workflows": len(workflows_module.workflows),
            "logs": len(logs_module.logs),
        }
    )
    return data
