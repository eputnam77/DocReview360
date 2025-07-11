"""Public vs internal status helpers."""

from __future__ import annotations

from typing import Dict

from .documents import documents
from .logs import logs
from .search import projects
from .workflows import workflows


def public_status() -> Dict[str, int]:
    """Return counts safe for public display."""
    return {"projects": len(projects), "documents": len(documents)}


def internal_status() -> Dict[str, int]:
    """Return extended status including internal metrics."""
    data = public_status()
    data.update({"workflows": len(workflows), "logs": len(logs)})
    return data
