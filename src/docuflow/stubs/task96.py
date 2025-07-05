"""Plugin developer guide stub."""

from __future__ import annotations

from . import record_task_completion


def format_plugin_guide(name: str) -> str:
    """Return minimal Markdown docs for ``name`` plugin."""
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    record_task_completion(96)
    return f"# Plugin {name}\n\nUsage docs."
